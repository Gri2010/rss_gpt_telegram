import os
import requests
import random
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

# Список популярных родов комнатных растений
HOUSEPLANTS = [
    "Monstera", "Philodendron", "Alocasia", "Anthurium", "Ficus", "Calathea", 
    "Sansevieria", "Zamioculcas", "Spathiphyllum", "Begonia", "Peperomia", 
    "Aloe", "Crassula", "Echeveria", "Dracaena", "Syngonium", "Hoya", "Orchidaceae"
]

def get_houseplant_data():
    genus = random.choice(HOUSEPLANTS)
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://powo.science.kew.org/api/2/search?q={genus}&perPage=20"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        if data.get('results'):
            # Выбираем случайный вид
            return random.choice(data['results'])
    except Exception as e:
        logger.error(f"Ошибка POWO: {e}")
    return None

def get_plant_image(plant_data):
    """Пытается найти фото: сначала в POWO, потом в Википедии"""
    name = plant_data.get('name')
    
    # 1. Проверяем, есть ли фото в самой базе POWO
    if plant_data.get('images'):
        # POWO иногда дает превью
        img_id = plant_data['images'][0].get('assetId')
        if img_id:
            return f"https://lh3.googleusercontent.com/{img_id}=s1200"

    # 2. Если в POWO нет, идем в Википедию (Wikimedia Commons)
    wiki_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "titles": name,
        "pithumbsize": 1000,
        "generator": "search",
        "gsrsearch": f"intitle:{name}",
        "gsrlimit": 1
    }
    try:
        r = requests.get(wiki_url, params=params, timeout=10)
        pages = r.json().get('query', {}).get('pages', {})
        for p in pages.values():
            if 'thumbnail' in p:
                return p['thumbnail']['source']
    except:
        pass
    return None

def analyze_with_market_ai(plant_data):
    name = plant_data.get('name')
    family = plant_data.get('family')
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    
    system_prompt = (
        "Ты — аналитик цветочного рынка Royal FloraHolland. Твоя задача — описать горшечное растение. "
        "Инструкция: "
        "1. Напиши русское название. "
        "2. Блок 'Биржевая сводка': Придумай актуальную цену в евро (от 5 до 150€) и опиши спрос на этот вид сейчас. "
        "3. Блок 'Уход': Как не загубить покупку (свет, полив). "
        "4. Почему это отличная инвестиция в интерьер. "
        "Стиль: Профессиональный, лаконичный. Используй HTML: <b>, <i>."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Вид: {name}. Семейство: {family}."}
        ],
        "temperature": 0.6
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"Аналитика по <b>{name}</b> временно недоступна."

def run_bot():
    plant = get_houseplant_data()
    if not plant:
        return

    image_url = get_plant_image(plant)
    ai_text = analyze_with_market_ai(plant)
    
    powo_link = f"https://powo.science.kew.org/taxon/{plant['fqId']}"
    
    full_post = (
        f"🪴 <b>Market Report: {plant['name']}</b>\n"
        f"────────────────────\n\n"
        f"{ai_text}\n\n"
        f"────────────────────\n"
        f"🔗 <a href='{powo_link}'>Kew Botanical Data</a>\n"
        f"#FloraHolland #Инвестиции #КомнатныеРастения"
    )

    # Отправка
    if image_url:
        send_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        data = {"chat_id": CHANNEL_ID, "photo": image_url, "caption": full_post, "parse_mode": "HTML"}
    else:
        send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CHANNEL_ID, "text": full_post, "parse_mode": "HTML"}

    res = requests.post(send_url, json=data)
    logger.info(f"Статус отправки: {res.status_code}")

if __name__ == "__main__":
    run_bot()
