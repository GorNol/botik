import asyncio
import os
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType

# --- 1. Настройка логирования ---
logging.basicConfig(level=logging.INFO)

# --- 2. Загрузка настроек из переменных окружения ---
# Токены нужно будет указать в панели Bothost, подробнее см. ниже
TG_TOKEN = os.getenv('TG_BOT_TOKEN')
VK_TOKEN = os.getenv('VK_GROUP_TOKEN')
VK_GROUP_ID = int(os.getenv('VK_GROUP_ID', 0))  # ID группы VK (число)

if not all([TG_TOKEN, VK_TOKEN, VK_GROUP_ID]):
    logging.error("Ошибка: не заданы все переменные окружения!")
    exit(1)

# --- 3. Инициализация клиентов ---
# Telegram
bot_tg = Bot(token=TG_TOKEN)
dp = Dispatcher()

# VK
vk_session = VkApi(token=VK_TOKEN)
vk_api = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

# --- 4. Обработчик команд в Telegram (например, /start) ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Бот запущен! Все сообщения из этого чата будут пересылаться в группу VK.")

# --- 5. Основной обработчик сообщений из Telegram в VK ---
@dp.message()
async def forward_to_vk(message: types.Message):
    try:
        # Формируем текст с именем автора
        user_name = message.from_user.full_name
        text_to_send = f"👤 {user_name} (TG):\n{message.text}"

        # Отправляем сообщение в VK
        vk_api.messages.send(
            peer_id=VK_GROUP_ID,  # ID группы или пользователя
            message=text_to_send,
            random_id=0
        )
        logging.info(f"Сообщение переслано в VK: {text_to_send}")
    except Exception as e:
        logging.error(f"Ошибка при отправке в VK: {e}")

# --- 6. Функция для прослушивания VK и пересылки в Telegram (Long Poll) ---
async def listen_vk():
    logging.info("Начинаем прослушивание VK Long Poll...")
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.text:
            # Игнорируем свои же сообщения, чтобы избежать циклов
            if event.from_me:
                continue

            text_to_send = f"👤 Пользователь VK:\n{event.text}"
            try:
                await bot_tg.send_message(chat_id=os.getenv('TG_CHAT_ID'), text=text_to_send)
                logging.info(f"Сообщение переслано в Telegram: {event.text}")
            except Exception as e:
                logging.error(f"Ошибка при отправке в Telegram: {e}")

# --- 7. Запуск ботов ---
async def main():
    # Запускаем прослушивание VK в отдельной задаче
    vk_task = asyncio.create_task(listen_vk())
    # Запускаем Telegram бота (поллинг)
    await dp.start_polling(bot_tg)

if __name__ == '__main__':
    asyncio.run(main())
