import os
import asyncio
import requests
import random
import logging
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Список растений (латынь)
PLANTS = [
    "Monstera deliciosa", "Alocasia baginda", "Philodendron erubescens",
    "Anthurium clarinervium", "Strelitzia nicolai", "Syngonium podophyllum",
    "Aglaonema commutatum", "Calathea orbifolia", "Scindapsus pictus",
    "Begonia maculata", "Ficus lyrata", "Zamioculcas zamiifolia"
]

def generate_expert_post(plant_name):
    """Имитация базы Kew Gardens через экспертные знания нейронки"""
    try:
        prompt = f"""
        Используй строгие научные данные (стандарт Kew Gardens / POWO).
        Напиши пост про растение: {plant_name}.
        
        Формат:
        🏛 **Научная классификация**
        - Вид: {plant_name}
        - Семейство: (укажи на латыни)
        
        🌍 **География (Native Range)**
        (Укажи точные регионы происхождения согласно базе POWO)
        
        🪴 **Культивация (Kew Standard)**
        - Субстрат: (профессиональный состав)
        - Свет и Влажность: (конкретные цифры и условия)
        
        🛡 **Патологии**
        (Типичные проблемы этого вида)

        Тон: Сухой, научный, профессиональный. Язык: Русский.
        """
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Ты — цифровой справочник Королевских ботанических садов Кью."},
                      {"role": "user", "content": prompt}],
            temperature=0.1 # Минимальная фантазия
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return None

def send_to_telegram(text, species_name):
    """Отправка в канал с качественным фото"""
    # Используем проверенный сервис фото (Unsplash)
    photo_url = f"https://source.unsplash.com/featured/1200x900/?houseplant,{species_name.replace(' ', ',')}"
    
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
            # Если фото не прошло (404), шлем просто текст
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        logger.error(f"Telegram Error: {e}")

async def main():
    plant = random.choice(PLANTS)
    logger.info(f"Формирую научную справку для: {plant}")
    
    final_post = generate_expert_post(plant)
    
    if final_post:
        send_to_telegram(final_post, plant)
        logger.info(f"Пост про {plant} успешно отправлен.")
    else:
        logger.error("Ошибка генерации контента.")

if __name__ == "__main__":
    asyncio.run(main())
