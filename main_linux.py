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
import tempfile
import pyautogui
import importlib.util

TOKEN = ""
TOKEN_INITIALIZED = False
USER_DATA_FILE = os.path.join(os.path.expanduser("~"), ".dm_bot", "user_data.json")
bot = None
VIDEO_RECORDING = False
ACCESS_CODE_TIMEOUT = 60
AUTHORIZED_USERS = {}
ACCESS_CODES = {}

def check_video_dependencies():
    try:
        importlib.import_module('imageio.plugins.ffmpeg')
        return True
    except ImportError:
        return False

def install_video_dependencies():
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio[ffmpeg]"])
        return True
    except subprocess.CalledProcessError:
        return False

def ensure_config_dir():
    config_dir = os.path.dirname(USER_DATA_FILE)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

def generate_access_code():
    random_string = secrets.token_hex(16)
    hashed_code = hashlib.sha256(random_string.encode()).hexdigest()
    return hashed_code, random_string

def verify_access_code(telegram_id, user_input):
    try:
        hashed_code, random_string = ACCESS_CODES[telegram_id]
    except KeyError:
        return False

    input_hashed_code = hashlib.sha256(user_input.encode()).hexdigest()
    return input_hashed_code == hashed_code

def clear_access_code(telegram_id):
    try:
        del ACCESS_CODES[telegram_id]
    except KeyError:
        pass

def load_user_data():
    global AUTHORIZED_USERS
    ensure_config_dir()
    try:
        with open(USER_DATA_FILE, "r") as f:
            AUTHORIZED_USERS = json.load(f)
    except FileNotFoundError:
        AUTHORIZED_USERS = {}
    except json.JSONDecodeError:
        print("Ошибка при чтении файла user_data.json. Файл будет перезаписан.")
        AUTHORIZED_USERS = {}

def save_user_data():
    try:
        with open(USER_DATA_FILE, "w") as f:
            json.dump(AUTHORIZED_USERS, f)
    except Exception as e:
        print(f"Ошибка при сохранении данных пользователей: {e}")

load_user_data()

def is_authorized(telegram_id):
    return AUTHORIZED_USERS.get(str(telegram_id), False)

def take_screenshot():
    try:
        with mss.mss() as sct:
            sct_img = sct.grab(sct.monitors[1])
            output = os.path.join(tempfile.gettempdir(), "screenshot.png")
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=output)
            return output, None
    except Exception as e:
        return None, f"Ошибка при создании скриншота: {e}"

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
            bot.send_message(message.chat.id, "Ошибка: Файл скриншота не найден.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при отправке скриншота: {e}")
        finally:
            try:
                os.remove(screenshot_file)
            except Exception as e:
                print(f"Ошибка при удалении временного файла: {e}")
    else:
        bot.send_message(message.chat.id, "Не удалось сделать скриншот.")

def record_screen(duration=10):
    global VIDEO_RECORDING
    VIDEO_RECORDING = True

    if not check_video_dependencies():
        if not install_video_dependencies():
            return None, "Для записи видео требуется установить дополнительные зависимости. Пожалуйста, выполните команду: pip install imageio[ffmpeg]"

    filename = os.path.join(tempfile.gettempdir(), "screen_record.mp4")
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
        return None, f"Ошибка при записи видео: {e}"
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
            bot.send_message(message.chat.id, "Ошибка: Файл видео не найден.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка при отправке видео: {e}")
        finally:
            try:
                os.remove(video_file)
            except Exception as e:
                print(f"Ошибка при удалении временного файла: {e}")
    else:
        bot.send_message(message.chat.id, "Не удалось записать видео.")

def shutdown_pc():
    try:
        subprocess.run(["shutdown", "-h", "now"])
        return "ПК выключается..."
    except Exception as e:
        return f"Ошибка при выключении ПК: {e}"

def lock_pc(message):
    try:
        subprocess.run(["xdg-screensaver", "lock"])
        bot.send_message(message.chat.id, "ПК заблокирован!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при блокировке ПК: {e}")

def authorized(func):
    def wrapper(message):
        telegram_id = str(message.from_user.id)

        if not is_authorized(telegram_id):
            if bot:
                bot.reply_to(message, "Вы не авторизованы. Пожалуйста, введите код доступа, отображаемый в консоли.")
                send_access_code_request(message)
            else:
                print("Бот не инициализирован. Пожалуйста, введите токен.")
            return

        return func(message)

    return wrapper

def start(message):
    telegram_id = str(message.from_user.id)

    if not is_authorized(telegram_id):
        if bot:
            bot.reply_to(message, "Вы не авторизованы. Пожалуйста, введите код доступа, отображаемый в консоли.")
            send_access_code_request(message)
        else:
            print("Бот не инициализирован. Пожалуйста, введите токен.")
        return

    show_main_menu(message)
    send_hello_message(message)

def send_access_code_request(message):
    telegram_id = str(message.from_user.id)
    hashed_code, random_string = generate_access_code()
    ACCESS_CODES[telegram_id] = (hashed_code, random_string)
    
    print(f"\nКод доступа: {random_string}")
    print("Введите этот код в Telegram бота для авторизации.")
    print("Код действителен в течение 60 секунд.\n")
    
    bot.send_message(message.chat.id, "Пожалуйста, введите код доступа, отображаемый в консоли.")

def process_access_code(message, telegram_id):
    user_input = message.text.strip()
    
    if verify_access_code(telegram_id, user_input):
        AUTHORIZED_USERS[telegram_id] = True
        save_user_data()
        clear_access_code(telegram_id)
        bot.reply_to(message, "Авторизация успешна!")
        show_main_menu(message)
    else:
        bot.reply_to(message, "Неверный код доступа. Попробуйте еще раз.")
        send_access_code_request(message)

def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        types.KeyboardButton("📸 Сделать скриншот"),
        types.KeyboardButton("🎥 Записать видео"),
        types.KeyboardButton("🔒 Заблокировать ПК"),
        types.KeyboardButton("🔄 Выключить ПК"),
        types.KeyboardButton("🗑 Очистить данные")
    ]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

def send_hello_message(message):
    bot.send_message(message.chat.id, "Привет! Я бот для удаленного управления компьютером.")

def clear_user_data(message):
    telegram_id = str(message.from_user.id)
    if telegram_id in AUTHORIZED_USERS:
        del AUTHORIZED_USERS[telegram_id]
        save_user_data()
        bot.reply_to(message, "Данные пользователя удалены.")
    else:
        bot.reply_to(message, "Данные пользователя не найдены.")

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

def register_handlers():
    bot.message_handler(commands=['start'])(start)
    bot.message_handler(func=lambda message: message.text == "📸 Сделать скриншот")(screenshot_button)
    bot.message_handler(func=lambda message: message.text == "🎥 Записать видео")(video_button)
    bot.message_handler(func=lambda message: message.text == "🔒 Заблокировать ПК")(lock_pc_button)
    bot.message_handler(func=lambda message: message.text == "🔄 Выключить ПК")(shutdown_button)
    bot.message_handler(func=lambda message: message.text == "🗑 Очистить данные")(clear_data_button)
    
    @bot.message_handler(func=lambda message: True)
    def handle_messages(message):
        telegram_id = str(message.from_user.id)
        if telegram_id in ACCESS_CODES:
            process_access_code(message, telegram_id)
        else:
            bot.reply_to(message, "Используйте меню для управления.")

def run_bot():
    global bot, TOKEN
    while not TOKEN:
        print("Пожалуйста, введите токен вашего бота:")
        TOKEN = input().strip()
    
    bot = telebot.TeleBot(TOKEN)
    register_handlers()
    print("\nБот запущен! Используйте /start в Telegram для начала работы.")
    print("Для выхода нажмите Ctrl+C\n")
    bot.polling(none_stop=True)

if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("\nБот остановлен.") 
