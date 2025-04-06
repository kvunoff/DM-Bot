# DM-Bot

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

MIT License

# DM-Bot
Distance Management Bot by kvunoff

# Russian

## Что такое DM-Bot?

### DM-Bot - это скрипт на Python, который поможет вам инициализировать своего собственного бота-помощника для управления вашим ПК!
В нем есть различные функции, такие как:
 - Быстрое получение **скриншота** с вашего ПК
 - Получение небольшого **видео** происходящего у вас на экране
 - Возможность **быстрой блокировки** вашего ПК
 - Возможность **экстренного выключения** вашего ПК
 - Управление **окнами** вашего ПК

Также есть и другие функции, часть из которых все еще в разработке!

## Преимущества перед другими, схожими ботами:
 - Код данного бота **уже скомпилирован** в `.exe`-файл. Это означает, что вам не требуется никаких знаний языка программирования.
 - Также, помимо скомпилированного файла, в открытом доступе есть исходный код для тех, кто не сильно доверяет мне или просто хочет изучить код подробнее.

# English

## What is DM-Bot?

### DM-Bot is a Python script that helps you initialize your own assistant bot to control your PC!
It has various functions such as:
 - Quickly taking a **screenshot** from your PC
 - Getting a short **video** of what's happening on your screen
 - The ability to **quickly lock** your PC
 - The ability to **urgently shut down** your PC
 - Managing your PC's **windows**

There are also other functions, some of which are still under development!

## Advantages over other similar bots:
 - The code of this bot is **already compiled** into a `.exe` file. This means that you do not need any knowledge of programming languages.
 - Also, in addition to the compiled file, the source code is publicly available for those who don't really trust me or just want to study the code in more detail.
