# DM-Bot
> [!IMPORTANT]
> ONLY LINUX DOCUMENTATION HERE. FOR WINDOWS JUST DOWNLOAD LAST .exe FILE FROM RELEASE PAGE. PROJECT IS ARCHIVED FOR WINDOWS.

Remote Linux PC control via Telegram.  
No GUI required — fully CLI-based.

## Install
```bash
curl -fsSL https://raw.githubusercontent.com/kvunoff/DM-Bot/main/install.sh | bash
```

## Setup

1. Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram
2. Run `dm-bot` — you'll be prompted for the token on first launch
3. Open your bot in Telegram and send `/auth`
4. Enter the code shown in your terminal

## Commands

| Command | Description |
|---|---|
| `/auth` | Authorize (requires physical access to the machine) |
| `/screenshot` | Take a screenshot |
| `/record [sec]` | Record screen (default 10s, max 60s) |
| `/sysinfo` | CPU, RAM, disk, uptime |
| `/lock` | Lock screen |
| `/shutdown` | Shut down PC |
| `/reboot` | Reboot |
| `/windows` | List open windows |
| `/win_action <action> <title>` | Manage a window |

## Autostart
```bash
dm-bot --install-service
systemctl --user start dm-bot
```

## Uninstall
```bash
curl -fsSL https://raw.githubusercontent.com/kvunoff/DM-Bot/main/uninstall.sh | bash
```

## Requirements

- Python 3.8+
- Linux with X11 or Wayland
- `wmctrl` / `xdotool` for window management (optional)

## License

MIT