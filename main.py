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
    "Монстера деликатесная", "Фикус Лирата", "Сансевиерия (Тещин язык)", "Замиокулькас (Долларовое дерево)", 
    "Стрелиция Николая", "Аглаонема", "Калатея Ората", "Эпипремнум золотистый",
    "Пилея пеперомиевидная", "Алоказия Полли", "Хлорофитум", "Антуриум (Мужское счастье)",
    "Драцена Маргината", "Спатифиллум (Женское счастье)", "Сциндапсус", "Хамедорея", 
    "Шеффлера", "Юкка слоновая", "Кротон", "Пеперомия арбузная", "Сингониум розовый"
]

def generate_plant_post(plant_name):
    try:
        # Улучшенный промпт, чтобы Groq не ленился
        prompt = f"""
        Напиши подробный и красивый пост для любителей домашних цветов про растение: {plant_name}.
        Обязательно включи разделы:
        1. 🌿 Описание (чем оно крутое).
        2. ☀️ Освещение.
        3. 💧 Полив.
        4. ✨ Секретный совет по уходу.
        
        Используй много тематических эмодзи. Пиши живым, человеческим языком.
        В конце добавь хештеги #растения #уход #дом.
        """
        
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": "Ты профессиональный биолог и популярный блогер по комнатным растениям. Пиши только на русском языке."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8, # Больше креатива
        )
        result = completion.choices[0].message.content
        if len(result) < 50: # Если выдал фигню, кидаем ошибку
            raise ValueError("Слишком короткий ответ от нейронки")
        return result
    except Exception as e:
        logger.error(f"Ошибка Groq: {e}")
        return f"🌿 <b>{plant_name}</b>\n\nК сожалению, детальное описание временно недоступно, но это растение — настоящий маст-хэв! Оно отлично очищает воздух и радует глаз своей зеленью. 💚"

def send_telegram_post(text, plant_name):
    # Источник фото без ограничений (Unsplash Source)
    photo_url = f"https://source.unsplash.com/featured/?houseplant,{plant_name.split()[0]}"
    
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
            # Если ошибка с фото, шлем просто текст
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"})
    except Exception as e:
        logger.error(f"Ошибка в ТГ: {e}")

async def run_once():
    plant = random.choice(PLANTS)
    logger.info(f"Генерирую большой пост для: {plant}")
    post_text = generate_plant_post(plant)
    send_telegram_post(post_text, plant)

if __name__ == "__main__":
    asyncio.run(run_once())
