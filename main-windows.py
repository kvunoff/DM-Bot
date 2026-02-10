import secrets
import telebot
from telebot import types
import sys
import os
import mss
import mss.tools
import subprocess
import time
import imageio
import numpy as np
import requests
from requests.exceptions import ConnectionError, ReadTimeout
import hashlib
import json
import tkinter as tk
from tkinter import messagebox
import pyperclip
import tempfile
import pygetwindow as gw

TOKEN = ""
TOKEN_INITIALIZED = False
if getattr(sys, 'frozen', False):
    USER_DATA_FILE = os.path.join(tempfile.gettempdir(), "user_data.json")
else:
    USER_DATA_FILE = "user_data.json"
bot = None
VIDEO_RECORDING = False
ACCESS_CODE_TIMEOUT = 60
AUTHORIZED_USERS = {}
ACCESS_CODES = {}


def generate_access_code():
    random_string = secrets.token_hex(16)
    hashed_code = hashlib.sha256(random_string.encode()).hexdigest()
    return hashed_code, random_string


def store_access_code(telegram_id, hashed_code, random_string):
    access_file = f"access_{telegram_id}.tmp"
    try:
        with open(access_file, "w") as file:
            file.write(f"{hashed_code}\n{random_string}")
        return access_file
    except Exception as e:
        print(f"Error creating access file: {e}")
        return None


def verify_access_code(telegram_id, user_input):
    try:
        hashed_code, random_string = ACCESS_CODES[telegram_id]
    except KeyError:
        return False

    input_hashed_code = hashlib.sha256(user_input.encode()).hexdigest()
    if input_hashed_code == hashed_code == hashed_code:
        return True
    else:
        return False


def clear_access_code(telegram_id):
    try:
        del ACCESS_CODES[telegram_id]
    except KeyError:
        pass


def load_user_data():
    global AUTHORIZED_USERS
    try:
        with open(USER_DATA_FILE, "r") as f:
            AUTHORIZED_USERS = json.load(f)
    except FileNotFoundError:
        AUTHORIZED_USERS = {}
    except json.JSONDecodeError:
        print("Error reading user_data.json. The file will be overwritten.")
        AUTHORIZED_USERS = {}


def save_user_data():
    try:
        with open(USER_DATA_FILE, "w") as f:
            json.dump(AUTHORIZED_USERS, f)
    except Exception as e:
        print(f"Error saving user data: {e}")


load_user_data()


def is_authorized(telegram_id):
    return AUTHORIZED_USERS.get(str(telegram_id), False)


def take_screenshot():
    try:
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[1])
            output = "screenshot.png"
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
            return output, None
    except Exception as e:
        return None, f"Error taking screenshot: {e}"


def send_screenshot(message):
    screenshot_file, error_message = take_screenshot()
    if error_message:
        bot.send_message(message.chat.id, error_message)
        return
    if screenshot_file:
        try:
            with open(screenshot_file, "rb") as photo:
                bot.send_photo(message.chat.id, photo)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "Error: Screenshot file not found.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Error sending screenshot: {e}")
        finally:
            try:
                os.remove(screenshot_file)
            except Exception as e:
                print(f"Error deleting temporary file: {e}")
    else:
        bot.send_message(message.chat.id, "Failed to take screenshot.")


def record_screen(duration=10):
    global VIDEO_RECORDING
    VIDEO_RECORDING = True

    if getattr(sys, 'frozen', False):
        temp_dir = tempfile.gettempdir()
    else:
        temp_dir = os.getcwd()
    filename = os.path.join(temp_dir, "screen_record.mp4")
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            width = monitor["width"]
            height = monitor["height"]

            writer = imageio.get_writer(filename, fps=20)

            start_time = time.time()
            while time.time() - start_time < duration and VIDEO_RECORDING:
                img = sct.grab(monitor)
                frame = np.array(img)

                if frame.shape[2] == 4:
                    frame = frame[:, :, [2, 1, 0, 3]]
                elif frame.shape[2] == 3:
                    frame = frame[:, :, [2, 1, 0]]

                writer.append_data(frame)

            writer.close()
        return filename, None
    except Exception as e:
        return None, f"Error recording video: {e}"
    finally:
        VIDEO_RECORDING = False


def send_video(message):
    video_file, error_message = record_screen()
    if error_message:
        bot.send_message(message.chat.id, error_message)
        return

    if video_file:
        try:
            with open(video_file, "rb") as video:
                bot.send_video(message.chat.id, video)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "Error: Video file not found.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Error sending video: {e}")
        finally:
            try:
                os.remove(video_file)
            except Exception as e:
                print(f"Error deleting temporary file: {e}")
    else:
        bot.send_message(message.chat.id, "Failed to record video.")


def shutdown_pc():
    try:
        subprocess.run(["shutdown", "/s", "/t", "1"])
        return "PC is shutting down..."
    except Exception as e:
        return f"Error shutting down PC: {e}"


def lock_pc(message):
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        bot.send_message(message.chat.id, "PC locked!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error locking PC: {e}")


def authorized(func):
    def wrapper(message):
        telegram_id = str(message.from_user.id)

        if not is_authorized(telegram_id):
            if bot:
                bot.reply_to(message,
                             "You are not authorized. Please copy the access code displayed on the computer screen. *CLOSE THE WINDOW WHERE YOU COPIED THE CODE BEFORE ENTERING IT*")
                send_access_code_request(message)
            else:
                print("Bot is not initialized. Please enter the token.")
            return

        return func(message)

    return wrapper


def start(message):
    telegram_id = str(message.from_user.id)

    if not is_authorized(telegram_id):
        if bot:
            bot.reply_to(message,
                         "You are not authorized. Please copy the access code displayed on the computer screen. *CLOSE THE WINDOW WHERE YOU COPIED THE CODE BEFORE ENTERING IT*")
            send_access_code_request(message)
        else:
            print("Bot is not initialized. Please enter the token.")
        return

    show_main_menu()
    send_hello_message(message)


def send_access_code_request(message):
    telegram_id = str(message.from_user.id)
    hashed_code, random_string = generate_access_code()

    ACCESS_CODES[telegram_id] = (hashed_code, random_string)

    show_access_code_window(random_string)

    bot.send_message(message.chat.id,
                     "Enter the access code you copied:")
    bot.register_next_step_handler(message, process_access_code, telegram_id)


def show_access_code_window(access_code):
    root = tk.Tk()
    root.title("Access Code")
    root.geometry("500x150")

    label = tk.Label(root, text="Your access code:", font=("Arial", 12))
    label.pack(pady=10)

    code_label = tk.Label(root, text=access_code, font=("Courier", 16, "bold"))
    code_label.pack(pady=5)

    def copy_to_clipboard():
        try:
            pyperclip.copy(access_code)
            messagebox.showinfo("Copied", "Access code copied to clipboard.")
        except pyperclip.PyperclipException:
            messagebox.showerror("Error",
                                 "Failed to copy to clipboard. You may need to install xclip or xsel.")

    copy_button = tk.Button(root, text="Copy code", command=copy_to_clipboard)
    copy_button.pack(pady=10)

    root.mainloop()


def process_access_code(message, telegram_id):
    user_input = message.text
    if verify_access_code(telegram_id, user_input):
        AUTHORIZED_USERS[str(telegram_id)] = True
        save_user_data()
        clear_access_code(telegram_id)
        bot.send_message(message.chat.id, "Code confirmed. Access granted.")
        show_main_menu()
        send_hello_message(message)
    else:
        bot.send_message(message.chat.id, "Invalid access code. Try again.")
        clear_access_code(telegram_id)


def show_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    lock_button = types.KeyboardButton("🔒 Lock PC")
    screenshot_button = types.KeyboardButton("📸 Screenshot")
    video_button = types.KeyboardButton("🎬 Record video")
    shutdown_button = types.KeyboardButton("🔌 Shut down PC")
    manage_windows_button = types.KeyboardButton("🪟 Window management")

    markup.add(lock_button, screenshot_button, video_button, shutdown_button, manage_windows_button)
    markup.add(types.KeyboardButton("🗑️ Clear data"))


def send_hello_message(message):
    bot.send_message(message.chat.id,
                     "Hello! I am a PC control bot. Press a button to lock, take a screenshot, record a video, clear data, or manage windows.")


def clear_user_data(message):
    global AUTHORIZED_USERS
    AUTHORIZED_USERS = {}
    save_user_data()
    bot.send_message(message.chat.id, "User data successfully cleared.")
    show_main_menu()


def list_windows():
    windows = gw.getAllTitles()
    return windows


def manage_window(action, window_title):
    try:
        window = gw.getWindowsWithTitle(window_title)[0]
        if action == "minimize":
            window.minimize()
            return f"Window '{window_title}' minimized."
        elif action == "maximize":
            window.maximize()
            return f"Window '{window_title}' maximized."
        elif action == "close":
            window.close()
            return f"Window '{window_title}' closed."
        else:
            return "Unknown action."
    except IndexError:
        return f"Window with title '{window_title}' not found."
    except Exception as e:
        return f"Error managing window: {e}"


@authorized
def window_management(message):
    windows = list_windows()
    if not windows:
        bot.send_message(message.chat.id, "No open windows.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for window in windows:
        markup.add(types.KeyboardButton(window))

    markup.add(types.KeyboardButton("Back"))
    bot.send_message(message.chat.id, "Select a window:", reply_markup=markup)

    bot.register_next_step_handler(message, process_window_selection)


def process_window_selection(message):
    selected_window = message.text
    if selected_window == "Back":
        show_main_menu()
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    minimize_button = types.KeyboardButton("Minimize")
    maximize_button = types.KeyboardButton("Maximize")
    close_button = types.KeyboardButton("Close")
    markup.add(minimize_button, maximize_button, close_button)

    bot.send_message(message.chat.id, f"You selected: {selected_window}. What do you want to do?", reply_markup=markup)

    bot.register_next_step_handler(message, lambda msg: perform_window_action(msg, selected_window))


def perform_window_action(message, window_title):
    action = message.text
    if action == "Minimize":
        result = manage_window("minimize", window_title)
    elif action == "Maximize":
        result = manage_window("maximize", window_title)
    elif action == "Close":
        result = manage_window("close", window_title)
    else:
        bot.send_message(message.chat.id, "Unknown action.")
        return

    bot.send_message(message.chat.id, result)
    show_main_menu()


def ask_for_token():
    root = tk.Tk()
    root.title("Enter Telegram bot token")
    root.geometry("300x150")

    label = tk.Label(root, text="Please enter your Telegram bot token:", font=("Arial", 10))
    label.pack(pady=10)

    token_entry = tk.Entry(root, width=40)
    token_entry.pack(pady=5)

    def save_token():
        global TOKEN, bot, TOKEN_INITIALIZED
        TOKEN = token_entry.get()
        if TOKEN:
            try:
                bot = telebot.TeleBot(TOKEN)
                TOKEN_INITIALIZED = True
                messagebox.showinfo("Success", "Token saved successfully. Bot initialized.")
                root.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid token or connection error: {e}")
        else:
            messagebox.showerror("Error", "Please enter a token.")

    save_button = tk.Button(root, text="Save token", command=save_token)
    save_button.pack(pady=10)

    root.mainloop()


def register_handlers():
    if bot:
        bot.message_handler(commands=['start'])(start)
        bot.message_handler(func=lambda message: message.text == "🔒 Lock PC")(lock_pc_button)
        bot.message_handler(func=lambda message: message.text == "📸 Screenshot")(screenshot_button)
        bot.message_handler(func=lambda message: message.text == "🎬 Record video")(video_button)
        bot.message_handler(func=lambda message: message.text == "🔌 Shut down PC")(shutdown_button)
        bot.message_handler(func=lambda message: message.text == "🗑️ Clear data")(clear_data_button)
        bot.message_handler(func=lambda message: message.text == "🪟 Window management")(
            window_management)
        bot.message_handler(commands=['lock'])(lock_pc_command)
        bot.message_handler(commands=['screenshot'])(screenshot_command)
        bot.message_handler(commands=['video'])(video_command)
        bot.message_handler(commands=['shutdown'])(shutdown_command)


@authorized
def lock_pc_button(message):
    lock_pc(message)


@authorized
def screenshot_button(message):
    send_screenshot(message)


@authorized
def video_button(message):
    send_video(message)


@authorized
def shutdown_button(message):
    result = shutdown_pc()
    bot.send_message(message.chat.id, result)


@authorized
def clear_data_button(message):
    clear_user_data(message)


@authorized
def lock_pc_command(message):
    lock_pc(message)


@authorized
def screenshot_command(message):
    send_screenshot(message)


@authorized
def video_command(message):
    send_video(message)


@authorized
def shutdown_command(message):
    result = shutdown_pc()
    bot.send_message(message.chat.id, result)


def run_bot():
    global bot, TOKEN_INITIALIZED

    if not TOKEN_INITIALIZED:
        ask_for_token()
        if not TOKEN_INITIALIZED:
            print("Token was not entered. Exiting program.")
            return

    register_handlers()

    connected = False
    while True:
        try:
            bot.polling(none_stop=True)
            if not connected:
                print("Successfully connected to Telegram API!")
                connected = True
        except (ConnectionError, ReadTimeout) as e:
            print(f"Connection error or timeout: {e}. Reconnecting in 10 seconds...")
            connected = False
            time.sleep(10)
        except Exception as e:
            print(f"Other error: {e}. Reconnecting in 10 seconds...")
            connected = False
            time.sleep(10)


if __name__ == '__main__':
    if sys.platform != "win32":
        print("This bot is designed for Windows only!")
    else:
        run_bot()
