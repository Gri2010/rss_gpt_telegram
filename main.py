import os
import asyncio
import requests
import random
import logging
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Проверенный список: Название - Прямая ссылка
PLANT_DATA = {
    "Monstera deliciosa": "https://upload.wikimedia.org/wikipedia/commons/0/04/Starr_080731-9572_Monstera_deliciosa.jpg",
    "Alocasia baginda": "https://upload.wikimedia.org/wikipedia/commons/e/e8/Alocasia_baginda_Dragon_Scale.jpg",
    "Anthurium clarinervium": "https://upload.wikimedia.org/wikipedia/commons/0/0c/Anthurium_clarinervium_1.jpg",
    "Ficus lyrata": "https://upload.wikimedia.org/wikipedia/commons/8/83/Ficus_lyrata_leaves_01.JPG",
    "Monstera adansonii": "https://upload.wikimedia.org/wikipedia/commons/1/1e/Monstera_adansonii_Lesser_Antilles.jpg",
    "Strelitzia nicolai": "https://upload.wikimedia.org/wikipedia/commons/a/a2/Strelitzia_nicolai_01.JPG",
    "Zamioculcas zamiifolia": "https://upload.wikimedia.org/wikipedia/commons/c/c2/Zamioculcas_zamiifolia_Garten-Zamioculcas.jpg",
    "Philodendron gloriosum": "https://upload.wikimedia.org/wikipedia/commons/b/ba/Philodendron_gloriosum_1.jpg"
}

def generate_expert_post(plant_name):
    try:
        # Просим нейронку использовать HTML теги вместо Markdown
        prompt = f"""
        Используй данные Kew Gardens и POWO. Напиши научную справку про {plant_name}.
        Используй ТОЛЬКО эти HTML теги: <b>...</b> для жирного, <i>...</i> для курсива.
        
        Структура:
        <b>🏛 Научная классификация</b>
        <b>🌍 География (Native Range)</b>
        <b>🪴 Культивация (Kew Standard)</b>
        <b>🛡 Патологии</b>
        
        Тон: Научный, сухой. Язык: Русский.
        """
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Ты — архив Kew Gardens. Выдаешь данные в HTML формате (b, i)."},
                      {"role": "user", "content": prompt}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return None

def send_to_telegram(text, photo_url):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHANNEL_ID,
        "caption": text[:1024], 
        "photo": photo_url,
        "parse_mode": "HTML" # Заменили на HTML для стабильности
    }
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            logger.error(f"Ошибка ТГ: {r.text}")
            # Если фото не прошло, пробуем отправить хотя бы текст
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"})
        else:
            logger.info("Пост с фото улетел!")
    except Exception as e:
        logger.error(f"Ошибка: {e}")

async def main():
    plant_name, photo_url = random.choice(list(PLANT_DATA.items()))
    logger.info(f"Запуск: {plant_name}")
    final_post = generate_expert_post(plant_name)
    if final_post:
        send_to_telegram(final_post, photo_url)

if __name__ == "__main__":
    asyncio.run(main())
