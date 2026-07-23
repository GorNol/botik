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
TG_TOKEN = os.getenv('TG_BOT_TOKEN')
VK_TOKEN = os.getenv('VK_GROUP_TOKEN')
VK_GROUP_ID = os.getenv('VK_GROUP_ID')  # Должен быть с минусом, например -123456789
TG_CHAT_ID = os.getenv('TG_CHAT_ID')    # Должен быть с минусом для группы, например -1001234567890

# Проверка, что все переменные заданы
if not all([TG_TOKEN, VK_TOKEN, VK_GROUP_ID, TG_CHAT_ID]):
    logging.error("Ошибка: не заданы все переменные окружения!")
    exit(1)

# Преобразуем VK_GROUP_ID в число (он уже должен быть с минусом)
try:
    VK_GROUP_ID = int(VK_GROUP_ID)
except ValueError:
    logging.error("Ошибка: VK_GROUP_ID должен быть числом (например, -123456789)")
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

# --- 5. Обработчик сообщений из Telegram → VK ---
@dp.message()
async def forward_to_vk(message: types.Message):
    try:
        # Игнорируем команды
        if message.text and message.text.startswith('/'):
            logging.info("Игнорируем команду")
            return

        # Логируем полученное сообщение
        logging.info(f"Получено сообщение из TG: {message.text}")

        user_name = message.from_user.full_name
        text_to_send = f"👤 {user_name} (TG):\n{message.text}"

        # Логируем, что пытаемся отправить
        logging.info(f"Пытаемся отправить в VK (peer_id={VK_GROUP_ID}): {text_to_send}")

        # Отправляем
        vk_api.messages.send(
            peer_id=VK_GROUP_ID,
            message=text_to_send,
            random_id=0
        )
        logging.info("✅ Сообщение успешно отправлено в VK")
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке в VK: {e}")
        # Выводим полную информацию об ошибке
        import traceback
        logging.error(traceback.format_exc())

# --- 6. Функция для прослушивания VK → Telegram (Long Poll) ---
async def listen_vk():
    logging.info("Начинаем прослушивание VK Long Poll...")
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.text:
            # Игнорируем свои же сообщения, чтобы избежать циклов
            if event.from_me:
                continue

            # Формируем текст для отправки в Telegram
            text_to_send = f"👤 Пользователь VK:\n{event.text}"
            try:
                await bot_tg.send_message(
                    chat_id=TG_CHAT_ID,  # ID группы Telegram (с минусом)
                    text=text_to_send
                )
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
