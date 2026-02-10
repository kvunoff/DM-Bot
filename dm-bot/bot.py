__version__ = "4.26.2.10"
__app_name__ = "DM-Bot"

import secrets
import hashlib
import json
import logging
import os
import sys
import time
import subprocess
import tempfile
import threading
import signal
from pathlib import Path
from functools import wraps
from typing import Optional

import mss
import mss.tools
import imageio
import numpy as np
import telebot
from telebot import types
from requests.exceptions import ConnectionError, ReadTimeout

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] dm-bot: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("dm-bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("dm-bot")

# ─────────────────────────────────────────────────────────────────────────────
# Constants & config
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("DM_BOT_DATA_DIR", Path.home() / ".config" / "dm-bot"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

USER_DATA_FILE = DATA_DIR / "authorized_users.json"
TOKEN_FILE     = DATA_DIR / "token.enc"

ACCESS_CODE_TTL      = 120   # seconds before an access code expires
VIDEO_DEFAULT_DURATION = 10  # seconds
VIDEO_MAX_DURATION   = 60    # cap to prevent abuse
MAX_FAILED_ATTEMPTS  = 5     # lockout threshold per session
LOCKOUT_DURATION     = 300   # 5-minute lockout after brute-force

# ─────────────────────────────────────────────────────────────────────────────
# Globals
# ─────────────────────────────────────────────────────────────────────────────

bot: Optional[telebot.TeleBot] = None
VIDEO_RECORDING = False

# telegram_id -> {"code": hashed, "plain": raw, "issued": timestamp}
ACCESS_CODES: dict = {}

# telegram_id -> True
AUTHORIZED_USERS: dict = {}

# telegram_id -> {"count": int, "locked_until": float}
FAILED_ATTEMPTS: dict = {}

# ─────────────────────────────────────────────────────────────────────────────
# User data persistence
# ─────────────────────────────────────────────────────────────────────────────

def load_user_data() -> None:
    global AUTHORIZED_USERS
    try:
        with open(USER_DATA_FILE, "r") as f:
            AUTHORIZED_USERS = json.load(f)
        log.info("Loaded %d authorized user(s).", len(AUTHORIZED_USERS))
    except FileNotFoundError:
        AUTHORIZED_USERS = {}
    except json.JSONDecodeError:
        log.error("Corrupted authorized_users.json — resetting.")
        AUTHORIZED_USERS = {}


def save_user_data() -> None:
    try:
        tmp = USER_DATA_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(AUTHORIZED_USERS, f, indent=2)
        tmp.replace(USER_DATA_FILE)
    except Exception as exc:
        log.error("Failed to save user data: %s", exc)

# ─────────────────────────────────────────────────────────────────────────────
# Token management
# ─────────────────────────────────────────────────────────────────────────────

def read_token_from_file() -> Optional[str]:
    """Read a previously saved token from ~/.config/dm-bot/token.enc"""
    try:
        token = TOKEN_FILE.read_text().strip()
        return token if token else None
    except FileNotFoundError:
        return None


def save_token_to_file(token: str) -> None:
    TOKEN_FILE.write_text(token)
    TOKEN_FILE.chmod(0o600)  # owner read/write only


def prompt_for_token() -> str:
    """Interactive CLI token prompt shown on first launch."""
    print("\n" + "═" * 60)
    print(f"  {__app_name__} v{__version__} — First-time setup")
    print("═" * 60)
    print("  Enter your Telegram Bot token.")
    print("  Get one from @BotFather on Telegram.")
    print(f"  Token will be saved to: {TOKEN_FILE}")
    print("═" * 60)
    while True:
        token = input("  Token: ").strip()
        if ":" in token and len(token) > 30:
            save_token_to_file(token)
            log.info("Token saved to %s", TOKEN_FILE)
            return token
        print("  [!] That doesn't look like a valid token. Try again.")

# ─────────────────────────────────────────────────────────────────────────────
# Authorization helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_authorized(telegram_id: str) -> bool:
    return bool(AUTHORIZED_USERS.get(telegram_id, False))


def is_locked_out(telegram_id: str) -> bool:
    entry = FAILED_ATTEMPTS.get(telegram_id)
    if not entry:
        return False
    if entry["locked_until"] > time.time():
        return True
    FAILED_ATTEMPTS.pop(telegram_id, None)
    return False


def record_failed_attempt(telegram_id: str) -> int:
    entry = FAILED_ATTEMPTS.setdefault(telegram_id, {"count": 0, "locked_until": 0.0})
    entry["count"] += 1
    if entry["count"] >= MAX_FAILED_ATTEMPTS:
        entry["locked_until"] = time.time() + LOCKOUT_DURATION
        log.warning(
            "DM-Bot: user %s locked out after %d failed auth attempts.",
            telegram_id, entry["count"],
        )
    return entry["count"]


def reset_failed_attempts(telegram_id: str) -> None:
    FAILED_ATTEMPTS.pop(telegram_id, None)

# ─────────────────────────────────────────────────────────────────────────────
# Access code system
# ─────────────────────────────────────────────────────────────────────────────

def generate_access_code() -> tuple[str, str]:
    """Return (hashed_code, plaintext_code). Uses 128-bit cryptographic entropy."""
    plain  = secrets.token_urlsafe(16)
    hashed = hashlib.sha256(plain.encode()).hexdigest()
    return hashed, plain


def store_access_code(telegram_id: str, hashed: str, plain: str) -> None:
    ACCESS_CODES[telegram_id] = {
        "code":   hashed,
        "plain":  plain,         # displayed once in terminal; never written to disk
        "issued": time.time(),
    }


def verify_access_code(telegram_id: str, user_input: str) -> bool:
    entry = ACCESS_CODES.get(telegram_id)
    if not entry:
        return False
    if time.time() - entry["issued"] > ACCESS_CODE_TTL:
        clear_access_code(telegram_id)
        log.info("DM-Bot: access code for %s expired.", telegram_id)
        return False
    # Constant-time comparison — prevents timing attacks
    input_hashed = hashlib.sha256(user_input.strip().encode()).hexdigest()
    return secrets.compare_digest(input_hashed, entry["code"])


def clear_access_code(telegram_id: str) -> None:
    ACCESS_CODES.pop(telegram_id, None)

# ─────────────────────────────────────────────────────────────────────────────
# Authorization decorator
# ─────────────────────────────────────────────────────────────────────────────

def authorized(func):
    @wraps(func)
    def wrapper(message: types.Message):
        tid = str(message.from_user.id)

        if is_locked_out(tid):
            remaining = int(FAILED_ATTEMPTS[tid]["locked_until"] - time.time())
            bot.reply_to(
                message,
                f"⛔ Too many failed attempts. Try again in {remaining}s.",
            )
            log.warning("DM-Bot: locked-out user %s attempted a command.", tid)
            return

        if not is_authorized(tid):
            bot.reply_to(
                message,
                "🔐 *DM-Bot:* you are not authorized.\n"
                "Use /auth to start the authorization process.",
                parse_mode="Markdown",
            )
            return

        return func(message)
    return wrapper

# ─────────────────────────────────────────────────────────────────────────────
# Console: access code display
# ─────────────────────────────────────────────────────────────────────────────

def display_access_code_on_console(plain_code: str, telegram_id: str) -> None:
    """Print the one-time access code in the terminal running DM-Bot."""
    border = "═" * 60
    log.info("DM-Bot: access code generated for Telegram ID %s", telegram_id)
    print("\n" + border)
    print("  🔑  DM-Bot — ACCESS CODE REQUEST")
    print(f"  Telegram ID : {telegram_id}")
    print(f"  Expires in  : {ACCESS_CODE_TTL}s")
    print(border)
    print(f"\n    {plain_code}\n")
    print(border + "\n")

# ─────────────────────────────────────────────────────────────────────────────
# Screenshot
# ─────────────────────────────────────────────────────────────────────────────

def take_screenshot() -> tuple[Optional[str], Optional[str]]:
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            outfile = str(DATA_DIR / f"dm-bot-screenshot-{int(time.time())}.png")
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=outfile)
            return outfile, None
    except Exception as exc:
        return None, f"DM-Bot screenshot error: {exc}"

# ─────────────────────────────────────────────────────────────────────────────
# Screen recording
# ─────────────────────────────────────────────────────────────────────────────

def record_screen(duration: int = VIDEO_DEFAULT_DURATION) -> tuple[Optional[str], Optional[str]]:
    global VIDEO_RECORDING
    duration = max(1, min(duration, VIDEO_MAX_DURATION))
    VIDEO_RECORDING = True
    outfile = str(DATA_DIR / f"dm-bot-record-{int(time.time())}.mp4")
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            writer  = imageio.get_writer(
                outfile, fps=15, codec="libx264",
                output_params=["-crf", "28"],
            )
            start = time.time()
            while time.time() - start < duration and VIDEO_RECORDING:
                frame = np.array(sct.grab(monitor))
                writer.append_data(frame[:, :, [2, 1, 0]])  # BGRA → RGB
            writer.close()
        return outfile, None
    except Exception as exc:
        return None, f"DM-Bot recording error: {exc}"
    finally:
        VIDEO_RECORDING = False

# ─────────────────────────────────────────────────────────────────────────────
# System commands
# ─────────────────────────────────────────────────────────────────────────────

def run_command(cmd: list[str], timeout: int = 10) -> tuple[str, str]:
    """Run a system command safely. Returns (stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return "", "Command timed out."
    except FileNotFoundError:
        return "", f"Command not found: {cmd[0]}"
    except Exception as exc:
        return "", str(exc)


def shutdown_pc() -> str:
    _, err = run_command(["shutdown", "-h", "now"])
    return err or "DM-Bot: shutdown initiated."


def reboot_pc() -> str:
    _, err = run_command(["shutdown", "-r", "now"])
    return err or "DM-Bot: reboot initiated."


def lock_screen() -> str:
    """Try common Linux screen lockers in order of preference."""
    lockers = [
        ["loginctl", "lock-session"],
        ["xdg-screensaver", "lock"],
        ["gnome-screensaver-command", "--lock"],
        ["xscreensaver-command", "--lock"],
        ["i3lock"],
    ]
    for cmd in lockers:
        _, err = run_command(cmd, timeout=5)
        if not err:
            return f"🔒 Screen locked via {cmd[0]}."
    return "❌ Could not lock screen — no supported locker found."


def list_windows() -> list[str]:
    """List open windows using wmctrl (preferred) or xdotool as fallback."""
    stdout, _ = run_command(["wmctrl", "-l"])
    if stdout:
        titles = []
        for line in stdout.splitlines():
            parts = line.split(None, 3)
            if len(parts) >= 4:
                titles.append(parts[3])
        return titles

    # Fallback: xdotool
    stdout, _ = run_command(["xdotool", "search", "--name", ""])
    if stdout:
        names = []
        for wid in stdout.splitlines()[:20]:
            name, _ = run_command(["xdotool", "getwindowname", wid])
            if name:
                names.append(f"{wid}: {name}")
        return names

    return []


def manage_window(action: str, window_title: str) -> str:
    """Minimize / maximize / close / activate a window by title substring."""
    if action == "minimize":
        ids_out, _ = run_command(["xdotool", "search", "--name", window_title])
        if not ids_out:
            return f"No window matching '{window_title}'."
        for wid in ids_out.splitlines():
            run_command(["xdotool", "windowminimize", wid])
        return f"Minimized window(s) matching '{window_title}'."

    action_map = {
        "close":    ["wmctrl", "-c", window_title],
        "maximize": ["wmctrl", "-r", window_title, "-b", "add,maximized_vert,maximized_horz"],
        "activate": ["wmctrl", "-a", window_title],
    }
    if action not in action_map:
        return f"Unknown action '{action}'. Use: minimize | maximize | close | activate"

    _, err = run_command(action_map[action])
    return f"Error: {err}" if err else f"Action '{action}' applied to '{window_title}'."


def get_system_info() -> str:
    """Return a brief system status block."""
    lines = [f"🖥  *DM-Bot — System Info*\n"]

    uptime, _ = run_command(["uptime", "-p"])
    if uptime:
        lines.append(f"⏱ Uptime: {uptime}")

    mem, _ = run_command(["free", "-h", "--si"])
    for line in (mem or "").splitlines():
        if line.startswith("Mem:"):
            parts = line.split()
            lines.append(f"🧠 RAM: {parts[2]} used / {parts[1]} total")

    disk, _ = run_command(["df", "-h", "--output=used,size,target", "/"])
    for line in (disk or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 3:
            lines.append(f"💾 Disk (/): {parts[0]} used / {parts[1]} total")

    cpu, _ = run_command(["top", "-bn1"])
    for line in (cpu or "").splitlines():
        if "%Cpu" in line or "Cpu(s)" in line:
            lines.append(f"🔲 CPU: {line.strip()}")
            break

    return "\n".join(lines) if len(lines) > 1 else "Could not retrieve system info."

# ─────────────────────────────────────────────────────────────────────────────
# Bot command handlers
# ─────────────────────────────────────────────────────────────────────────────

def cmd_start(message: types.Message) -> None:
    tid = str(message.from_user.id)
    if is_authorized(tid):
        send_main_menu(message)
    else:
        bot.reply_to(
            message,
            f"👋 *Welcome to DM-Bot v{__version__}*\n\n"
            "Remote control for your Linux PC via Telegram.\n\n"
            "You need to authorize first — use /auth to begin.",
            parse_mode="Markdown",
        )


def cmd_help(message: types.Message) -> None:
    text = (
        f"📖 *DM-Bot v{__version__} — Commands*\n\n"
        "*Authorization*\n"
        "/start — Welcome screen\n"
        "/auth — Authorize (requires access to the machine)\n"
        "/deauth — Revoke your own authorization\n\n"
        "*Screen*\n"
        "/screenshot — Take a screenshot\n"
        "/record \\[sec\\] — Record screen (default 10s, max 60s)\n\n"
        "*System*\n"
        "/sysinfo — CPU, RAM, disk, uptime\n"
        "/lock — Lock screen\n"
        "/shutdown — Shut down PC (asks confirmation)\n"
        "/reboot — Reboot PC\n\n"
        "*Windows*\n"
        "/windows — List open windows\n"
        "/win\\_action \\<action\\> \\<title\\> — Manage a window\n"
        "  `actions: minimize | maximize | close | activate`\n\n"
        "*Admin*\n"
        "/cleardata — Remove all authorized users\n"
        "/version — Show DM-Bot version\n"
        "/help — Show this message"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


def cmd_version(message: types.Message) -> None:
    bot.reply_to(message, f"*DM-Bot* v{__version__}", parse_mode="Markdown")


def cmd_auth(message: types.Message) -> None:
    tid = str(message.from_user.id)

    if is_authorized(tid):
        bot.reply_to(message, "✅ You are already authorized in DM-Bot.")
        return

    if is_locked_out(tid):
        remaining = int(FAILED_ATTEMPTS[tid]["locked_until"] - time.time())
        bot.reply_to(message, f"⛔ DM-Bot: locked out. Try again in {remaining}s.")
        return

    hashed, plain = generate_access_code()
    store_access_code(tid, hashed, plain)
    display_access_code_on_console(plain, tid)

    bot.send_message(
        message.chat.id,
        f"🔑 *DM-Bot Authorization*\n\n"
        f"A one-time access code has been printed in the *terminal where DM-Bot is running*.\n\n"
        f"⚠️ Physical access to the machine is required to see it.\n\n"
        f"The code expires in *{ACCESS_CODE_TTL} seconds*.\n\n"
        "Enter the code:",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(message, process_access_code, tid)


def process_access_code(message: types.Message, tid: str) -> None:
    user_input = message.text or ""
    if verify_access_code(tid, user_input):
        reset_failed_attempts(tid)
        AUTHORIZED_USERS[tid] = True
        save_user_data()
        clear_access_code(tid)
        log.info("DM-Bot: user %s authorized successfully.", tid)
        bot.send_message(
            message.chat.id,
            "✅ *DM-Bot:* authorization successful. Access granted.",
            parse_mode="Markdown",
        )
        send_main_menu(message)
    else:
        attempts = record_failed_attempt(tid)
        clear_access_code(tid)
        if is_locked_out(tid):
            bot.send_message(
                message.chat.id,
                f"❌ *DM-Bot:* wrong code. Too many attempts — locked out for {LOCKOUT_DURATION}s.",
                parse_mode="Markdown",
            )
        else:
            remaining_tries = MAX_FAILED_ATTEMPTS - attempts
            bot.send_message(
                message.chat.id,
                f"❌ *DM-Bot:* wrong code. {remaining_tries} attempt(s) remaining.\n"
                "Use /auth to try again.",
                parse_mode="Markdown",
            )
        log.warning("DM-Bot: failed auth attempt for %s (attempt #%d).", tid, attempts)


@authorized
def cmd_deauth(message: types.Message) -> None:
    tid = str(message.from_user.id)
    AUTHORIZED_USERS.pop(tid, None)
    save_user_data()
    bot.reply_to(message, "🔓 *DM-Bot:* your authorization has been revoked.", parse_mode="Markdown")
    log.info("DM-Bot: user %s deauthorized themselves.", tid)


@authorized
def cmd_screenshot(message: types.Message) -> None:
    bot.send_chat_action(message.chat.id, "upload_photo")
    path, err = take_screenshot()
    if err:
        bot.reply_to(message, f"❌ {err}")
        return
    try:
        with open(path, "rb") as f:
            bot.send_photo(message.chat.id, f, caption="📸 DM-Bot screenshot")
    finally:
        Path(path).unlink(missing_ok=True)


@authorized
def cmd_record(message: types.Message) -> None:
    global VIDEO_RECORDING
    if VIDEO_RECORDING:
        bot.reply_to(message, "⚠️ DM-Bot: a recording is already in progress.")
        return

    args = message.text.split()
    duration = VIDEO_DEFAULT_DURATION
    if len(args) > 1:
        try:
            duration = int(args[1])
        except ValueError:
            bot.reply_to(message, "Usage: /record [seconds]")
            return

    bot.reply_to(message, f"🎬 *DM-Bot:* recording for {duration}s — please wait.", parse_mode="Markdown")

    def do_record():
        path, err = record_screen(duration)
        if err:
            bot.send_message(message.chat.id, f"❌ {err}")
            return
        try:
            bot.send_chat_action(message.chat.id, "upload_video")
            with open(path, "rb") as f:
                bot.send_video(message.chat.id, f, caption=f"🎬 DM-Bot — {duration}s recording")
        finally:
            Path(path).unlink(missing_ok=True)

    threading.Thread(target=do_record, daemon=True).start()


@authorized
def cmd_sysinfo(message: types.Message) -> None:
    bot.reply_to(message, get_system_info(), parse_mode="Markdown")


@authorized
def cmd_lock(message: types.Message) -> None:
    bot.reply_to(message, lock_screen())


@authorized
def cmd_shutdown(message: types.Message) -> None:
    bot.reply_to(
        message,
        "⚠️ *DM-Bot:* are you sure you want to shut down?\n"
        "Reply /confirm\\_shutdown to proceed, or anything else to cancel.",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(message, _confirm_shutdown)


def _confirm_shutdown(message: types.Message) -> None:
    if message.text and message.text.strip() == "/confirm_shutdown":
        bot.reply_to(message, "🔌 *DM-Bot:* shutting down...", parse_mode="Markdown")
        log.warning("DM-Bot: shutdown triggered by Telegram user %s.", message.from_user.id)
        shutdown_pc()
    else:
        bot.reply_to(message, "✅ *DM-Bot:* shutdown cancelled.", parse_mode="Markdown")


@authorized
def cmd_reboot(message: types.Message) -> None:
    bot.reply_to(message, "♻️ *DM-Bot:* rebooting...", parse_mode="Markdown")
    log.warning("DM-Bot: reboot triggered by Telegram user %s.", message.from_user.id)
    reboot_pc()


@authorized
def cmd_windows(message: types.Message) -> None:
    wins = list_windows()
    if not wins:
        bot.reply_to(
            message,
            "❌ *DM-Bot:* no open windows found.\n"
            "Make sure wmctrl or xdotool is installed.",
            parse_mode="Markdown",
        )
        return
    text = "🪟 *DM-Bot — Open windows:*\n\n" + "\n".join(f"• {w}" for w in wins[:30])
    bot.reply_to(message, text, parse_mode="Markdown")


@authorized
def cmd_win_action(message: types.Message) -> None:
    parts = message.text.split(None, 2)
    if len(parts) < 3:
        bot.reply_to(
            message,
            "*DM-Bot:* usage: `/win_action <action> <window title>`\n"
            "Actions: `minimize` | `maximize` | `close` | `activate`",
            parse_mode="Markdown",
        )
        return
    action, title = parts[1].lower(), parts[2]
    result = manage_window(action, title)
    bot.reply_to(message, result)


@authorized
def cmd_cleardata(message: types.Message) -> None:
    global AUTHORIZED_USERS
    count = len(AUTHORIZED_USERS)
    AUTHORIZED_USERS = {}
    save_user_data()
    log.warning("DM-Bot: authorized_users.json cleared by %s (removed %d user(s)).",
                message.from_user.id, count)
    bot.reply_to(
        message,
        f"🗑️ *DM-Bot:* cleared {count} authorized user(s).",
        parse_mode="Markdown",
    )


def send_main_menu(message: types.Message) -> None:
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        types.KeyboardButton("📸 Screenshot"),
        types.KeyboardButton("🎬 Record video"),
    )
    markup.row(
        types.KeyboardButton("🔒 Lock screen"),
        types.KeyboardButton("ℹ️ System info"),
    )
    markup.row(
        types.KeyboardButton("🪟 List windows"),
        types.KeyboardButton("📖 Help"),
    )
    markup.row(types.KeyboardButton("🔌 Shutdown"))
    bot.send_message(
        message.chat.id,
        f"✅ *DM-Bot v{__version__}* — authorized.\n"
        "Use the buttons below or /help for all commands.",
        reply_markup=markup,
        parse_mode="Markdown",
    )

# ─────────────────────────────────────────────────────────────────────────────
# Button text → handler map
# ─────────────────────────────────────────────────────────────────────────────

BUTTON_MAP = {
    "📸 Screenshot":  cmd_screenshot,
    "🎬 Record video": cmd_record,
    "🔒 Lock screen":  cmd_lock,
    "ℹ️ System info":  cmd_sysinfo,
    "🪟 List windows": cmd_windows,
    "📖 Help":         cmd_help,
    "🔌 Shutdown":     cmd_shutdown,
}


def handle_text(message: types.Message) -> None:
    handler = BUTTON_MAP.get(message.text)
    if handler:
        handler(message)

# ─────────────────────────────────────────────────────────────────────────────
# Handler registration
# ─────────────────────────────────────────────────────────────────────────────

def register_handlers() -> None:
    bot.message_handler(commands=["start"])(cmd_start)
    bot.message_handler(commands=["help"])(cmd_help)
    bot.message_handler(commands=["version"])(cmd_version)
    bot.message_handler(commands=["auth"])(cmd_auth)
    bot.message_handler(commands=["deauth"])(cmd_deauth)
    bot.message_handler(commands=["screenshot"])(cmd_screenshot)
    bot.message_handler(commands=["record"])(cmd_record)
    bot.message_handler(commands=["sysinfo"])(cmd_sysinfo)
    bot.message_handler(commands=["lock"])(cmd_lock)
    bot.message_handler(commands=["shutdown"])(cmd_shutdown)
    bot.message_handler(commands=["reboot"])(cmd_reboot)
    bot.message_handler(commands=["windows"])(cmd_windows)
    bot.message_handler(commands=["win_action"])(cmd_win_action)
    bot.message_handler(commands=["cleardata"])(cmd_cleardata)
    bot.message_handler(func=lambda m: m.text in BUTTON_MAP)(handle_text)

# ─────────────────────────────────────────────────────────────────────────────
# Graceful shutdown
# ─────────────────────────────────────────────────────────────────────────────

def handle_signal(sig, frame) -> None:
    log.info("DM-Bot: signal %s received — stopping.", sig)
    if bot:
        bot.stop_polling()
    sys.exit(0)

# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    global bot

    signal.signal(signal.SIGINT,  handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    load_user_data()

    # Token priority: env var → saved file → interactive prompt
    token = (
        os.environ.get("DM_BOT_TOKEN")
        or read_token_from_file()
        or prompt_for_token()
    )

    try:
        bot = telebot.TeleBot(token, parse_mode=None)
        me  = bot.get_me()
        log.info("DM-Bot: authenticated as @%s (id=%s)", me.username, me.id)
    except Exception as exc:
        log.error("DM-Bot: failed to initialize — %s", exc)
        sys.exit(1)

    register_handlers()

    print("\n" + "═" * 60)
    print(f"  DM-Bot v{__version__}")
    print(f"  Telegram bot : @{me.username}")
    print(f"  Data dir     : {DATA_DIR}")
    print(f"  Log file     : dm-bot.log")
    print(f"  Token env    : DM_BOT_TOKEN")
    print("  Press Ctrl+C to stop.")
    print("═" * 60 + "\n")

    log.info("DM-Bot v%s started. Polling...", __version__)

    reconnect_delay = 5
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=20)
        except (ConnectionError, ReadTimeout) as exc:
            log.warning("DM-Bot: network error (%s) — retrying in %ds.", exc, reconnect_delay)
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)
        except Exception as exc:
            log.error("DM-Bot: unexpected error (%s) — retrying in %ds.", exc, reconnect_delay)
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        print("DM-Bot is designed for Linux. Windows is not supported.")
        sys.exit(1)
    run()