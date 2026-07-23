import asyncio
import os
import logging
import threading
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from vk_api import VkApi
from vk_api.longpoll import VkLongPoll, VkEventType

logging.basicConfig(level=logging.INFO)

TG_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')  # ID чата, куда бот будет писать в TG
VK_TOKEN = os.getenv('VK_GROUP_TOKEN')
VK_PEER_ID = os.getenv('VK_PEER_ID')  # ID пользователя или беседы в ВК (куда писать)

if not all([TG_TOKEN, TG_CHAT_ID, VK_TOKEN, VK_PEER_ID]):
    logging.error("Ошибка: не заданы все переменные окружения (TG_BOT_TOKEN, TG_CHAT_ID, VK_GROUP_TOKEN, VK_PEER_ID)!")
    exit(1)

bot_tg = Bot(token=TG_TOKEN)
dp = Dispatcher()
vk_session = VkApi(token=VK_TOKEN)
vk_api = vk_session.get_api()
longpoll = VkLongPoll(vk_session)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 Бот запущен! Все сообщения из этого чата будут пересылаться в группу VK.")

@dp.message()
async def forward_to_vk(message: types.Message):
    if not message.text:
        return
        
    user_name = message.from_user.full_name
    text_to_send = f"👤 {user_name} (TG):\n{message.text}"
    
    try:
        await asyncio.to_thread(
            vk_api.messages.send,
            peer_id=int(VK_PEER_ID),
            message=text_to_send,
            random_id=0
        )
        logging.info(f"TG -> VK: {message.text}")
    except Exception as e:
        logging.error(f"Ошибка отправки в VK: {e}")

def listen_vk_loop(loop):
    logging.info("VK Long Poll запущен...")
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.text:
            if event.from_me:
                continue

            text_to_send = f"👤 Пользователь VK:\n{event.text}"
            
            asyncio.run_coroutine_threadsafe(
                bot_tg.send_message(chat_id=TG_CHAT_ID, text=text_to_send),
                loop
            )
            logging.info(f"VK -> TG: {event.text}")

async def main():
    loop = asyncio.get_running_loop()
    
    threading.Thread(target=listen_vk_loop, args=(loop,), daemon=True).start()
    
    await dp.start_polling(bot_tg)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
