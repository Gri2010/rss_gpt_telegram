import os
import asyncio
import requests
import random
import logging
from pykew.powo import Powo
from groq import Groq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Инициализация
powo = Powo()
groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Список реальных ID растений из базы Kew (POWO)
# Каждое ID соответствует конкретному виду
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
        res = powo.lookup(powo_id, include=['distribution'])
        name = res.get('name', 'Unknown')
        family = res.get('family', 'Unknown')
        dist_list = res.get('distribution', {}).get('natives', [])
        native_range = ", ".join([d.get('name') for d in dist_list[:5]])
        return f"Species: {name}\nFamily: {family}\nNative Range: {native_range}"
    except Exception as e:
        logger.error(f"Kew API Error: {e}")
        return None

def generate_expert_post(raw_data):
    """Перевод и экспертная обработка через Groq"""
    try:
        prompt = f"""
        Ты — эксперт-ботаник, работающий с архивами Kew Gardens. 
        Переведи и расширь эти данные до полноценного поста для экспертов:
        {raw_data}

        Формат:
        1. 🏛 **Научная классификация** (Латынь, семейство).
        2. 🌍 **География** (Где встречается в природе).
        3. 🪴 **Содержание в коллекции** (Субстрат, влажность, свет по стандартам оранжерей).
        4. 🛡 **Проблемы** (Болезни/вредители).
        
        Тон: Строгий, научный, профессиональный. Никакой воды.
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
    # Ищем фото по латинскому названию
    photo_url = f"https://source.unsplash.com/1600x900/?{species_name.replace(' ', ',')}"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHANNEL_ID,
        "caption": text[:1024], # Лимит ТГ на описание
        "photo": photo_url,
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
    logger.info("Запуск процесса...")
    p_id = random.choice(PLANT_IDS)
    raw_kew_info = get_kew_data(p_id)
    
    if raw_kew_info:
        # Выдергиваем название для поиска фото
        species_name = raw_kew_info.split('\n')[0].replace('Species: ', '')
        final_post = generate_expert_post(raw_kew_info)
        send_to_telegram(final_post, species_name)
        logger.info(f"Пост про {species_name} успешно отправлен.")
    else:
        logger.error("Не удалось получить данные из Kew.")

if __name__ == "__main__":
    asyncio.run(main())
