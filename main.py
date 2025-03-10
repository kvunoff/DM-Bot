
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
        print(f"Ошибка при создании файла доступа: {e}")
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
            output = "screenshot.png"
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
        subprocess.run(["shutdown", "/s", "/t", "1"])
        return "ПК выключается..."
    except Exception as e:
        return f"Ошибка при выключении ПК: {e}"

def lock_pc(message):
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        bot.send_message(message.chat.id, "ПК заблокирован!")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка при блокировке ПК: {e}")

def authorized(func):
    def wrapper(message):
        telegram_id = str(message.from_user.id)

        if not is_authorized(telegram_id):
            if bot:
                bot.reply_to(message,
                             "Вы не авторизованы. Пожалуйста, скопируйте код доступа, отображаемый на экране компьютера. *ПЕРЕД ВВОДОМ КОДА ЗАКРОЙТЕ ОКНО, ГДЕ ВЫ ЕГО КОПИРОВАЛИ*")
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
            bot.reply_to(message,
                         "Вы не авторизованы. Пожалуйста, скопируйте код доступа, отображаемый на экране компьютера. *ПЕРЕД ВВОДОМ КОДА ЗАКРОЙТЕ ОКНО, ГДЕ ВЫ ЕГО КОПИРОВАЛИ*")
            send_access_code_request(message)
        else:
            print("Бот не инициализирован. Пожалуйста, введите токен.")
        return

    show_main_menu(message)

def send_access_code_request(message):
    telegram_id = str(message.from_user.id)
    hashed_code, random_string = generate_access_code()

    ACCESS_CODES[telegram_id] = (hashed_code, random_string)

    show_access_code_window(random_string)

    bot.send_message(message.chat.id,
                     "Введите код доступа, который вы скопировали:")
    bot.register_next_step_handler(message, process_access_code, telegram_id)

def show_access_code_window(access_code):
    root = tk.Tk()
    root.title("Код доступа")
    root.geometry("500x150")

    label = tk.Label(root, text="Ваш код доступа:", font=("Arial", 12))
    label.pack(pady=10)

    code_label = tk.Label(root, text=access_code, font=("Courier", 16, "bold"))
    code_label.pack(pady=5)

    def copy_to_clipboard():
        try:
            pyperclip.copy(access_code)
            messagebox.showinfo("Скопировано", "Код доступа скопирован в буфер обмена.")
        except pyperclip.PyperclipException:
            messagebox.showerror("Ошибка",
                                 "Не удалось скопировать в буфер обмена. Возможно, требуется установить xclip или xsel.")

    copy_button = tk.Button(root, text="Копировать код", command=copy_to_clipboard)
    copy_button.pack(pady=10)

    root.mainloop()

def process_access_code(message, telegram_id):
    user_input = message.text
    if verify_access_code(telegram_id, user_input):
        AUTHORIZED_USERS[str(telegram_id)] = True
        save_user_data()
        clear_access_code(telegram_id)
        bot.send_message(message.chat.id, "Код подтвержден. Доступ к боту предоставлен.")
        show_main_menu(message)
    else:
        bot.send_message(message.chat.id, "Неверный код доступа. Попробуйте еще раз.")
        clear_access_code(telegram_id)

def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    lock_button = types.KeyboardButton("🔒 Заблокировать ПК")
    screenshot_button = types.KeyboardButton("📸 Скриншот")
    video_button = types.KeyboardButton("🎬 Записать видео")
    shutdown_button = types.KeyboardButton("🔌 Выключить ПК")
    clear_data_button = types.KeyboardButton("🗑️ Очистить данные")
    markup.add(lock_button, screenshot_button, video_button, shutdown_button, clear_data_button)
    bot.send_message(message.chat.id,
                     "Привет! Я бот для управления ПК. Нажмите кнопку, чтобы заблокировать, сделать скриншот, записать видео или очистить данные.",
                     reply_markup=markup)

def clear_user_data(message):
    global AUTHORIZED_USERS
    AUTHORIZED_USERS = {}
    save_user_data()
    bot.send_message(message.chat.id, "Данные пользователей успешно очищены.")
    show_main_menu(message)

def ask_for_token():
    root = tk.Tk()
    root.title("Введите токен Telegram-бота")
    root.geometry("300x150")

    label = tk.Label(root, text="Пожалуйста, введите токен вашего Telegram-бота:", font=("Arial", 10))
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
                messagebox.showinfo("Успех", "Токен успешно сохранен. Бот инициализирован.")
                root.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Неверный токен или ошибка при подключении: {e}")
        else:
            messagebox.showerror("Ошибка", "Пожалуйста, введите токен.")

    save_button = tk.Button(root, text="Сохранить токен", command=save_token)
    save_button.pack(pady=10)

    root.mainloop()

def register_handlers():
    if bot:
        bot.message_handler(commands=['start'])(start)
        bot.message_handler(func=lambda message: message.text == "🔒 Заблокировать ПК")(lock_pc_button)
        bot.message_handler(func=lambda message: message.text == "📸 Скриншот")(screenshot_button)
        bot.message_handler(func=lambda message: message.text == "🎬 Записать видео")(video_button)
        bot.message_handler(func=lambda message: message.text == "🔌 Выключить ПК")(shutdown_button)
        bot.message_handler(func=lambda message: message.text == "🗑️ Очистить данные")(clear_data_button)
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
            print("Токен не был введен. Выход из программы.")
            return

    register_handlers()

    connected = False
    while True:
        try:
            bot.polling(none_stop=True)
            if not connected:
                print("Успешное подключение к Telegram API!")
                connected = True
        except (ConnectionError, ReadTimeout) as e:
            print(f"Ошибка соединения или таймаут: {e}. Переподключение через 10 секунд...")
            connected = False
            time.sleep(10)
        except Exception as e:
            print(f"Другая ошибка: {e}. Переподключение через 10 секунд...")
            connected = False
            time.sleep(10)

if __name__ == '__main__':
    if sys.platform != "win32":
        print("Этот бот предназначен только для Windows!")
    else:
        run_bot()
