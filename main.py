import os
import asyncio
import requests
import random
import logging
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Список видов (латынь)
PLANTS = [
    "Monstera deliciosa", "Alocasia baginda", "Philodendron erubescens",
    "Anthurium clarinervium", "Strelitzia nicolai", "Syngonium podophyllum",
    "Aglaonema commutatum", "Calathea orbifolia", "Scindapsus pictus",
    "Ficus lyrata", "Zamioculcas zamiifolia", "Alocasia frydek", 
    "Philodendron gloriosum", "Monstera adansonii", "Anthurium crystallinum"
]

def generate_expert_post(plant_name):
    try:
        prompt = f"Напиши научную справку по стандарту Kew Gardens/POWO про {plant_name}: классификация, география (Native Range), субстрат, свет, влажность и патологии. Тон: научный. Язык: Русский."
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Ты — справочник Kew Gardens. Пиши строго по делу, используй Markdown."},
                      {"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return None

def send_to_telegram(text, species_name):
    # Прямая ссылка на надежный фото-генератор
    # Используем сразу 3 варианта на случай сбоя
    search_query = species_name.replace(" ", ",")
    photo_urls = [
        f"https://loremflickr.com/1200/900/{search_query},plant/all",
        f"https://api.dupondi.us/render?search={search_query}",
        "https://images.unsplash.com/photo-1463936575829-25148e1db1b8?q=80&w=1200" # Запасное
    ]

    success = False
    for url in photo_urls:
        if success: break
        
        tg_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        payload = {
            "chat_id": CHANNEL_ID,
            "caption": text[:1024], 
            "photo": url,
            "parse_mode": "Markdown"
        }
        
        try:
            r = requests.post(tg_url, json=payload)
            if r.status_code == 200:
                success = True
                logger.info(f"Фото отправлено успешно через {url}")
            else:
                logger.warning(f"Ошибка при отправке фото: {r.text}")
        except Exception as e:
            logger.error(f"Ошибка сети: {e}")

    if not success:
        # Если совсем всё плохо с фото — шлем текст
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"})

async def main():
    plant = random.choice(PLANTS)
    final_post = generate_expert_post(plant)
    if final_post:
        send_to_telegram(final_post, plant)

if __name__ == "__main__":
    asyncio.run(main())
