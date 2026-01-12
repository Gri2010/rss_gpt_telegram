import os
import asyncio
import requests
import random
import logging
import pykew.powo as powo
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Список ID растений (POWO ID)
PLANT_IDS = [
    '422969-1',  # Monstera deliciosa
    '277839-2',  # Alocasia baginda
    '425175-1',  # Philodendron erubescens
    '1123013-2', # Anthurium clarinervium
    '157053-1',  # Strelitzia nicolai
    '290354-2',  # Syngonium podophyllum
    '190225-2',  # Aglaonema commutatum
    '225121-2'   # Calathea orbifolia
]

def get_kew_data(powo_id):
    """Получает научные данные напрямую из Kew Gardens"""
    try:
        # Исправленный метод обращения к API pykew
        res = powo.lookup(powo_id, include=['distribution'])
        name = res.get('name', 'Unknown')
        family = res.get('family', 'Unknown')
        
        # Собираем ареал
        dist_list = res.get('distribution', {}).get('natives', [])
        native_range = ", ".join([d.get('name') for d in dist_list[:5]]) if dist_list else "Unknown"
        
        return f"Species: {name}\nFamily: {family}\nNative Range: {native_range}"
    except Exception as e:
        logger.error(f"Kew API Error: {e}")
        return None

def generate_expert_post(raw_data):
    """Перевод и экспертная обработка через Groq"""
    try:
        prompt = f"""
        Ты — эксперт-ботаник Kew Gardens. 
        Переведи и расширь эти данные до полноценного экспертного поста:
        {raw_data}

        Формат:
        1. 🏛 **Научная классификация** (Латынь, семейство).
        2. 🌍 **География** (Где встречается в природе).
        3. 🪴 **Содержание в коллекции** (Субстрат, влажность, свет по стандартам оранжерей).
        4. 🛡 **Проблемы** (Болезни/вредители).
        
        Тон: Строгий, научный. Никакой воды.
        """
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Ты — профессиональный таксономист."},
                      {"role": "user", "content": prompt}],
            temperature=0.2
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq Error: {e}")
        return raw_data

def send_to_telegram(text, species_name):
    """Отправка в канал с фото"""
    # Поиск фото по латинскому названию
    photo_query = species_name.replace(' ', ',')
    photo_url = f"https://images.unsplash.com/photo-1545241047-6083a3684587?q=80&w=1000&auto=format&fit=crop" # Заглушка, если поиск упадет
    
    # Пытаемся собрать живую ссылку на фото
    search_url = f"https://source.unsplash.com/featured/1600x900/?houseplant,{photo_query}"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHANNEL_ID,
        "caption": text[:1024], 
        "photo": search_url,
        "parse_mode": "Markdown"
    }
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            # Если фото не прошло, шлем просто текст
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        logger.error(f"Telegram Error: {e}")

async def main():
    p_id = random.choice(PLANT_IDS)
    logger.info(f"Запрос данных для ID: {p_id}")
    raw_kew_info = get_kew_data(p_id)
    
    if raw_kew_info:
        species_name = raw_kew_info.split('\n')[0].replace('Species: ', '')
        final_post = generate_expert_post(raw_kew_info)
        send_to_telegram(final_post, species_name)
        logger.info(f"Пост про {species_name} отправлен.")

if __name__ == "__main__":
    asyncio.run(main())
