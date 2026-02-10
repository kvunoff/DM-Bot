#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/dm-bot"
BIN_FILE="${HOME}/.local/bin/dm-bot"
SERVICE_FILE="${HOME}/.config/systemd/user/dm-bot.service"

echo "Uninstalling DM-Bot..."

[ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR" && echo "  ✓ Removed $INSTALL_DIR"
[ -f "$BIN_FILE"    ] && rm -f  "$BIN_FILE"    && echo "  ✓ Removed $BIN_FILE"

if [ -f "$SERVICE_FILE" ]; then
    systemctl --user stop    dm-bot.service 2>/dev/null || true
    systemctl --user disable dm-bot.service 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo "  ✓ Removed systemd service"
fi

echo ""
echo "DM-Bot has been uninstalled."
echo "Your config (~/.config/dm_bot/) was kept. Remove manually if needed."