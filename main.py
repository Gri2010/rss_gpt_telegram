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

# Список популярных родов горшечных растений (для фильтрации POWO)
HOUSEPLANTS = [
    "Monstera", "Philodendron", "Alocasia", "Anthurium", "Ficus", "Calathea", 
    "Sansevieria", "Zamioculcas", "Spathiphyllum", "Begonia", "Peperomia", 
    "Succulents", "Aloe", "Crassula", "Echeveria", "Dracaena", "Syngonium"
]

def get_houseplant_data():
    """Ищет конкретно комнатное растение из базы Кью"""
    genus = random.choice(HOUSEPLANTS)
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://powo.science.kew.org/api/2/search?q={genus}&perPage=20"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        if data.get('results'):
            # Выбираем случайный вид из популярного комнатного рода
            return random.choice(data['results'])
    except Exception as e:
        logger.error(f"Ошибка POWO: {e}")
    return None

def get_wikimedia_image(name):
    """Ищет фото растения"""
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "format": "json", "prop": "pageimages",
        "titles": name, "pithumbsize": 800, "generator": "search", "gsrsearch": name, "gsrlimit": 1
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        pages = r.json().get('query', {}).get('pages', {})
        for p in pages.values():
            if 'thumbnail' in p: return p['thumbnail']['source']
    except: pass
    return None

def analyze_with_market_ai(plant_data):
    """AI делает разбор: уход + данные 'а-ля биржа'"""
    name = plant_data.get('name')
    family = plant_data.get('family')
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    
    system_prompt = (
        "Ты — аналитик цветочного рынка и эксперт по комнатным растениям. "
        "Опиши растение для цветоводов и коллекционеров: "
        "1. Русское название и краткая справка. "
        "2. Блок 'Рыночный потенциал': оцени популярность этого вида на голландских аукционах (высокая/средняя/редкий коллекционный экземпляр). "
        "3. Блок 'Домашний уход': свет, полив, сложность. "
        "4. Почему его стоит купить в коллекцию. "
        "Стиль: деловой, экспертный, с долей энтузиазма. HTML разметка: <b>, <i>."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Вид: {name}. Семейство: {family}."}
        ],
        "temperature": 0.5
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"Карточка растения <b>{name}</b> готовится к выпуску."

def run_bot():
    plant = get_houseplant_data()
    if not plant: return

    image_url = get_wikimedia_image(plant['name'])
    ai_text = analyze_with_market_ai(plant)
    
    powo_link = f"https://powo.science.kew.org/taxon/{plant['fqId']}"
    
    full_post = (
        f"🪴 <b>Market Review: {plant['name']}</b>\n"
        f"────────────────────\n\n"
        f"{ai_text}\n\n"
        f"────────────────────\n"
        f"🔗 <a href='{powo_link}'>Botanical Data (Kew)</a>\n"
        f"#Горшечные #FloraHolland #КомнатныеРастения"
    )

    send_url = f"https://api.telegram.org/bot{TOKEN}/" + ("sendPhoto" if image_url else "sendMessage")
    payload = {"chat_id": CHANNEL_ID, "parse_mode": "HTML"}
    
    if image_url:
        payload["photo"] = image_url
        payload["caption"] = full_post
    else:
        payload["text"] = full_post

    requests.post(send_url, json=payload)

if __name__ == "__main__":
    run_bot()
