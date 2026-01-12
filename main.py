import os
import asyncio
import requests
import random
import logging
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

client = Groq(api_key=GROQ_KEY)

PLANTS = [
    "Монстера деликатесная", "Фикус Лирата", "Сансевиерия", "Замиокулькас", 
    "Стрелиция Николая", "Аглаонема", "Калатея Ората", "Эпипремнум золотистый",
    "Пилея пеперомиевидная", "Алоказия Полли", "Хлорофитум", "Антуриум",
    "Драцена Маргината", "Спатифиллум", "Сциндапсус", "Хамедорея", "Шеффлера",
    "Юкка", "Кротон", "Пеперомия", "Сингониум", "Бегония макулата"
]

def generate_plant_post(plant_name):
    try:
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Ты эксперт-ботаник. Пиши на русском языке полезные посты для Telegram. Используй эмодзи."},
                {"role": "user", "content": f"Напиши короткий пост про комнатное растение {plant_name}. Укажи 3 совета: свет, полив и влажность. В конце добавь интересный факт."}
            ],
            temperature=0.7,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"🌿 <b>{plant_name}</b>\nПрекрасное растение для уюта в доме!"

def send_telegram_post(text, plant_name):
    # Берем случайное фото из базы Unsplash по названию растения
    photo_url = f"https://source.unsplash.com/1600x900/?houseplant,{plant_name}"
    
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
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"})
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

async def run_once():
    plant = random.choice(PLANTS)
    logger.info(f"Работаем над: {plant}")
    post_text = generate_plant_post(plant)
    send_telegram_post(post_text, plant)
    logger.info("Готово.")

if __name__ == "__main__":
    asyncio.run(run_once())
