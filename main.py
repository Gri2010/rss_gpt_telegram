import os
import asyncio
import requests
import random
import logging
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Секреты
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

client = Groq(api_key=GROQ_KEY)

# Список популярных растений для базы
PLANTS = [
    "Монстера деликатесная", "Фикус Лирата", "Сансевиерия", "Замиокулькас", 
    "Стрелиция Николая", "Аглаонема", "Калатея Ората", "Эпипремнум золотистый",
    "Пилея пеперомиевидная", "Алоказия Полли", "Хлорофитум", "Антуриум"
]

def generate_plant_post(plant_name):
    """Генерирует текст через Groq"""
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Ты эксперт по комнатным растениям. Пиши краткие, полезные и вдохновляющие посты для Telegram. Используй эмодзи."},
                {"role": "user", "content": f"Напиши пост про растение: {plant_name}. Укажи кратко: освещение, полив и одну интересную фишку."}
            ],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка Groq: {e}")
        return f"🌿 <b>{plant_name}</b>\nПрекрасное растение для вашего дома! Скоро здесь будет описание ухода."

def send_telegram_post(text, plant_name):
    """Отправляет пост в канал с фото из интернета"""
    # Поиск фото через бесплатный источник (Unsplash) или просто текст
    photo_url = f"https://source.unsplash.com/featured/?{plant_name.replace(' ', ',')},plant"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHANNEL_ID,
        "caption": text,
        "photo": photo_url,
        "parse_mode": "HTML"
    }
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            # Если фото не прошло, шлем просто текст
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"})
        logger.info(f"Пост про {plant_name} отправлен!")
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

async def main_loop():
    logger.info("Бот-энциклопедия запущен!")
    while True:
        plant = random.choice(PLANTS)
        logger.info(f"Генерирую пост про {plant}...")
        
        post_text = generate_plant_post(plant)
        send_telegram_post(post_text, plant)
        
        # Ждем 1 час (3600 секунд)
        logger.info("Спим 1 час...")
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main_loop())
