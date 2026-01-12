import os
import asyncio
import requests
import random
import logging
from groq import Groq

# Логирование для отладки в GitHub Actions
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Секреты
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Проверенная база: Название растения и прямая ссылка на качественное фото (Wikipedia/Static)
PLANT_DATA = {
    "Monstera deliciosa": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/Starr_080731-9572_Monstera_deliciosa.jpg/800px-Starr_080731-9572_Monstera_deliciosa.jpg",
    "Alocasia baginda": "https://upload.wikimedia.org/wikipedia/commons/e/e8/Alocasia_baginda_Dragon_Scale.jpg",
    "Anthurium clarinervium": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/Anthurium_clarinervium_1.jpg/800px-Anthurium_clarinervium_1.jpg",
    "Ficus lyrata": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Ficus_lyrata_leaves_01.JPG/800px-Ficus_lyrata_leaves_01.JPG",
    "Monstera adansonii": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Monstera_adansonii_Lesser_Antilles.jpg/800px-Monstera_adansonii_Lesser_Antilles.jpg",
    "Strelitzia nicolai": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a2/Strelitzia_nicolai_01.JPG/800px-Strelitzia_nicolai_01.JPG",
    "Zamioculcas zamiifolia": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/Zamioculcas_zamiifolia_Garten-Zamioculcas.jpg/800px-Zamioculcas_zamiifolia_Garten-Zamioculcas.jpg",
    "Philodendron gloriosum": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/ba/Philodendron_gloriosum_1.jpg/800px-Philodendron_gloriosum_1.jpg"
}

def generate_expert_post(plant_name):
    """Генерация строгого научного текста через Groq"""
    try:
        prompt = f"""
        Используй строгие данные Kew Gardens и базы POWO. 
        Напиши ботаническую справку про {plant_name}.
        
        Обязательно включи:
        1. 🏛 Научная классификация (Латынь, Семейство).
        2. 🌍 География (Native Range по POWO).
        3. 🪴 Культивация (Субстрат, свет, влажность по стандартам оранжерей).
        4. 🛡 Патологии (Болезни и вредители).
        
        Тон: Научный, сухой. Язык: Русский. Используй Markdown для заголовков.
        """
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Ты — цифровой архив Kew Gardens. Выдаешь только факты без воды."},
                      {"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return None

def send_to_telegram(text, photo_url):
    """Отправка поста с фото в Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHANNEL_ID,
        "caption": text[:1024], 
        "photo": photo_url,
        "parse_mode": "Markdown"
    }
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            logger.error(f"Telegram API Error: {r.text}")
            # Если фото не проходит, отправляем хотя бы текст
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"})
        else:
            logger.info("Пост успешно отправлен!")
    except Exception as e:
        logger.error(f"Network Error: {e}")

async def main():
    # Выбираем случайное растение из базы
    plant_name, photo_url = random.choice(list(PLANT_DATA.items()))
    logger.info(f"Начинаю работу над: {plant_name}")
    
    final_post = generate_expert_post(plant_name)
    if final_post:
        send_to_telegram(final_post, photo_url)
    else:
        logger.error("Не удалось сгенерировать текст.")

if __name__ == "__main__":
    asyncio.run(main())
