# DM-Bot

# Русский

Telegram бот для удаленного управления компьютером (Windows и Linux).

## Что такое DM-Bot?

DM-Bot - это скрипт на Python, который поможет вам инициализировать своего собственного бота-помощника для управления вашим ПК!

### Основные функции:
- 📸 Быстрое получение **скриншота** с вашего ПК
- 🎥 Получение небольшого **видео** происходящего у вас на экране
- 🔒 Возможность **быстрой блокировки** вашего ПК
- 🔄 Возможность **экстренного выключения** вашего ПК
- 🗑 Управление данными пользователей

## Установка

### Windows

1. Скачайте файл `DM-Bot.exe` из раздела Releases
2. Запустите скачанный файл
3. Введите токен бота, когда программа попросит
4. Следуйте инструкциям в консоли

### Linux

1. Убедитесь, что у вас установлен Python 3.8 или выше:
```bash
python3 --version
```

2. Установите необходимые системные зависимости:
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-tk python3-dev ffmpeg
```

3. Клонируйте репозиторий или скачайте файлы:
```bash
git clone https://github.com/yourusername/DM-Bot.git
cd DM-Bot
```

4. Установите зависимости Python. Есть несколько способов:

   а) Установка через requirements.txt (рекомендуемый способ):
   ```bash
   pip3 install -r requirements.txt
   ```

   б) Установка каждой библиотеки отдельно:
   ```bash
   pip3 install setuptools>=65.5.1
   pip3 install pyTelegramBotAPI==4.14.0
   pip3 install mss==9.0.1
   pip3 install imageio==2.33.1
   pip3 install "imageio[ffmpeg]"
   pip3 install numpy==1.26.3
   pip3 install requests==2.31.0
   pip3 install pyautogui==0.9.54
   ```

   в) Установка для текущего пользователя (если нет прав root):
   ```bash
   pip3 install --user -r requirements.txt
   ```

5. Если возникают проблемы с правами доступа при установке, используйте:
```bash
sudo pip3 install -r requirements.txt
```

## Настройка бота

1. Запустите Telegram
2. Найдите бота @BotFather
3. Отправьте команду `/newbot`
4. Следуйте инструкциям для создания нового бота
5. Сохраните токен бота, который вам отправит BotFather

## Запуск бота

### Windows
1. Запустите `DM-Bot.exe`
2. Введите токен бота, когда программа попросит
3. Отправьте команду `/start` в Telegram боту
4. Введите код доступа, который появится в консоли

### Linux
1. Запустите бота:
```bash
python3 linux_bot.py
```

2. Введите токен бота, когда программа попросит
3. Отправьте команду `/start` в Telegram боту
4. Введите код доступа, который появится в консоли

## Безопасность

- Бот требует авторизации через код доступа
- Код доступа действителен в течение 60 секунд
- Данные пользователей хранятся в зашифрованном виде
- Все действия требуют подтверждения

## Требования к системе

### Windows
- Windows 10 или выше
- Установленный Telegram

### Linux
- Linux (Ubuntu, Debian или совместимые)
- Python 3.8 или выше
- Установленный Telegram

## Решение проблем

### Windows
- Если бот не запускается, убедитесь что у вас установлены все необходимые Visual C++ Redistributable
- Если не работает блокировка экрана, проверьте права доступа

### Linux
Если возникают проблемы с правами доступа:
```bash
sudo chmod +x linux_bot.py
```

Если не работает блокировка экрана, установите xdg-screensaver:
```bash
sudo apt-get install xdg-screensaver
```

Если не работает запись видео, убедитесь что установлен ffmpeg:
```bash
sudo apt-get install ffmpeg
pip3 install "imageio[ffmpeg]"
```

## Преимущества

- Код бота доступен в открытом доступе для изучения
- Простой интерфейс управления через Telegram
- Безопасная авторизация через код доступа
- Кроссплатформенность (Windows и Linux)
- Быстрый доступ к основным функциям управления ПК

## Лицензия

Вы можете увидеть лицензию [ЗДЕСЬ](https://tuqise.ru/license)

# English

Telegram bot for remote control of a computer (Windows and Linux).

## What is DM-Bot?

DM-Bot is a Python script that will help you initialize your own assistant bot to control your PC!

### Main features:
- 📸 Quickly get a **screenshot** from your PC
- 🎥 Get a small **video** of what's happening on your screen
- 🔒 Ability to **quickly lock** your PC
- 🔄 Ability to **emergency shut down** your PC
- 🗑 Manage user data

## Installation

### Windows

1. Download the `DM-Bot.exe` file from the Releases section
2. Run the downloaded file
3. Enter the bot token when prompted
4. Follow the instructions in the console

### Linux

1. Make sure you have Python 3.8 or higher installed:
```bash
python3 --version
```

2. Install the necessary system dependencies:
```bash
sudo apt-get update
sudo apt-get install python3-pip python3-tk python3-dev ffmpeg
```

3. Clone the repository or download the files:
```bash
git clone https://github.com/yourusername/DM-Bot.git
cd DM-Bot
```

4. Install Python dependencies. There are several ways:

a) Installation via requirements.txt (recommended method):
```bash
pip3 install -r requirements.txt
```

b) Installation of each library separately:
```bash
pip3 install setuptools>=65.5.1
pip3 install pyTelegramBotAPI==4.14.0
pip3 install mss==9.0.1
pip3 install imageio==2.33.1
pip3 install "imageio[ffmpeg]"
pip3 install numpy==1.26.3
pip3 install requests==2.31.0
pip3 install pyautogui==0.9.54
```

c) Installation for the current user (if there are no root rights):
```bash
pip3 install --user -r requirements.txt
```

5. If there are problems with access rights when installation, use:
```bash
sudo pip3 install -r requirements.txt
```

## Setting up the bot

1. Launch Telegram
2. Find the @BotFather bot
3. Send the command `/newbot`
4. Follow the instructions to create a new bot
5. Save the bot token that BotFather sends you

## Launching the bot

### Windows
1. Launch `DM-Bot.exe`
2. Enter the bot token when prompted
3. Send the command `/start` to the Telegram bot
4. Enter the access code that will appear in the console

### Linux
1. Launch the bot:
```bash
python3 linux_bot.py
```

2. Enter the bot token when prompted
3. Send the command `/start` to the Telegram bot
4. Enter the access code that will appear in the consoles

## Security

- The bot requires authorization via an access code
- The access code is valid for 60 seconds
- User data is stored encrypted
- All actions require confirmation

## System requirements

### Windows
- Windows 10 or higher
- Telegram installed

### Linux
- Linux (Ubuntu, Debian or compatible)
- Python 3.8 or higher
- Telegram installed

## Troubleshooting

### Windows
- If the bot does not start, make sure that you have all the necessary Visual C++ Redistributable installed
- If the screen lock does not work, check the access rights

### Linux
If there are problems with access rights:
```bash
sudo chmod +x linux_bot.py
```

If the screen lock does not work, install xdg-screensaver:
```bash
sudo apt-get install xdg-screensaver
```

If it does not work video recording, make sure ffmpeg is installed:
```bash
sudo apt-get install ffmpeg
pip3 install "imageio[ffmpeg]"
```

## Advantages

- The bot code is available in the public domain for study
- Simple control interface via Telegram
- Secure authorization via access code
- Cross-platform (Windows and Linux)
- Quick access to basic PC control functions

## License

You can see licnse [HERE](https://tuqise.ru/license)


