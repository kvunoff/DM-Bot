#!/usr/bin/env bash
set -euo pipefail

APP_NAME="dm-bot"
REPO_URL="https://github.com/kvunoff/DM-Bot"
RAW_URL="https://raw.githubusercontent.com/kvunoff/DM-Bot/main"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/dm-bot"
BIN_DIR="${HOME}/.local/bin"
BIN_FILE="${BIN_DIR}/dm-bot"

BOLD="\033[1m"; CYAN="\033[36m"; GREEN="\033[32m"
YELLOW="\033[33m"; RED="\033[31m"; RESET="\033[0m"
info()  { echo -e "${CYAN}[*]${RESET} $*"; }
ok()    { echo -e "${GREEN}[✓]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[!]${RESET} $*"; }
die()   { echo -e "${RED}[✗]${RESET} $*" >&2; exit 1; }

echo -e "\n${BOLD}DM-Bot Installer${RESET}"
echo "────────────────────────────────────────"

command -v python3 >/dev/null 2>&1 || die "Python 3 not found. Install it: sudo apt install python3"
command -v curl    >/dev/null 2>&1 || die "curl not found. Install it: sudo apt install curl"

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info[:2] >= (3,8))')
[ "$PYTHON_VERSION" = "True" ] || die "Python 3.8+ required."

ok "Python $(python3 --version)"

info "Creating directories..."
mkdir -p "$INSTALL_DIR/dm_bot"
mkdir -p "$BIN_DIR"

info "Downloading DM-Bot..."
curl -fsSL "${RAW_URL}/dm_bot/bot.py"       -o "${INSTALL_DIR}/dm_bot/bot.py"
curl -fsSL "${RAW_URL}/requirements.txt"    -o "${INSTALL_DIR}/requirements.txt"
ok "Files downloaded"

info "Creating Python virtual environment..."
python3 -m venv "${INSTALL_DIR}/.venv"
ok "Virtualenv created"

info "Installing Python dependencies..."
"${INSTALL_DIR}/.venv/bin/pip" install --quiet --upgrade pip
"${INSTALL_DIR}/.venv/bin/pip" install --quiet -r "${INSTALL_DIR}/requirements.txt"
ok "Dependencies installed"

info "Creating dm-bot command..."
cat > "$BIN_FILE" << SCRIPT
#!/usr/bin/env bash
exec "${INSTALL_DIR}/.venv/bin/python" "${INSTALL_DIR}/dm_bot/bot.py" "\$@"
SCRIPT
chmod +x "$BIN_FILE"
ok "Command created: dm-bot"

echo ""
info "Optional system packages for window management:"
for pkg in wmctrl xdotool; do
    if command -v "$pkg" >/dev/null 2>&1; then
        ok "$pkg — found"
    else
        warn "$pkg — not found (install: sudo apt install $pkg)"
    fi
done

echo ""
if [[ ":$PATH:" != *":${BIN_DIR}:"* ]]; then
    warn "${BIN_DIR} is not in your PATH."
    echo "   Add this to your ~/.bashrc or ~/.zshrc:"
    echo -e "   ${BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${RESET}"
    echo "   Then run: source ~/.bashrc"
else
    ok "${BIN_DIR} is in PATH"
fi

echo ""
echo -e "${GREEN}${BOLD}✓ DM-Bot installed successfully!${RESET}"
echo ""
echo "  Start the bot:   dm-bot"
echo "  Show help:       dm-bot --help"
echo "  Uninstall:       curl -fsSL ${RAW_URL}/uninstall.sh | bash"
echo ""