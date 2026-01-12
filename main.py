import os
import requests
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

# Топ коммерческих родов для Flowersale / FloraHolland
COMMERCIAL_LIST = [
    "Anthurium", "Phalaenopsis", "Spathiphyllum", "Monstera", "Dracaena", 
    "Ficus Benjamina", "Calathea", "Hydrangea", "Kalanchoe", "Rosa"
]

def get_commercial_plant():
    genus = random.choice(COMMERCIAL_LIST)
    headers = {"User-Agent": "Mozilla/5.0"}
    # Ищем конкретно коммерческие принятые виды
    url = f"https://powo.science.kew.org/api/2/search?q={genus}&perPage=10"
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
        if data.get('results'):
            return random.choice(data['results'])
    except Exception as e:
        logger.error(f"Ошибка POWO: {e}")
    return None

def get_wikimedia_image(name):
    wiki_url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "format": "json", "prop": "pageimages",
        "titles": name, "pithumbsize": 1000, "generator": "search", 
        "gsrsearch": f"intitle:{name}", "gsrlimit": 1
    }
    try:
        r = requests.get(wiki_url, params=params, timeout=10)
        pages = r.json().get('query', {}).get('pages', {})
        for p in pages.values():
            if 'thumbnail' in p: return p['thumbnail']['source']
    except: pass
    return None

def analyze_for_buyer(plant_data):
    name = plant_data.get('name')
    family = plant_data.get('family')
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    
    system_prompt = (
        "Ты — эксперт по закупкам на аукционе FloraHolland (через Flowersale). "
        "Опиши растение для байера. Сделай акцент на качестве товара: "
        "1. Название на русском и латыни. "
        "2. Характеристики лота: Опиши стандартные параметры (диаметр горшка, количество бутонов/цветоносов). "
        "3. Логистика: Насколько растение капризно при транспортировке (температурный режим +15°C или +2°C). "
        "4. Рыночный прогноз: Оцени востребованность в рознице и примерную вилку цен на аукционе. "
        "Стиль: Профессиональный сленг закупщиков. Используй HTML: <b>, <i>."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Товар: {name}. Группа: {family}."}
        ],
        "temperature": 0.6
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"Сводка по лоту <b>{name}</b> не сформирована."

def run_bot():
    plant = get_commercial_plant()
    if not plant: return

    image_url = get_wikimedia_image(plant['name'])
    ai_text = analyze_for_buyer(plant)
    
    full_post = (
        f"💹 <b>Биржевая сводка Flowersale: {plant['name']}</b>\n"
        f"────────────────────\n\n"
        f"{ai_text}\n\n"
        f"────────────────────\n"
        f"🚛 <i>Проверьте доступность лота в личном кабинете flowersale.nl</i>\n"
        f"#Закупки #ЦветочныйБизнес #Flowersale"
    )

    if image_url:
        send_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        res = requests.post(send_url, json={
            "chat_id": CHANNEL_ID, "photo": image_url, "caption": full_post, "parse_mode": "HTML"
        })
        if res.status_code == 200: return

    # Запасной текстовый вариант
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                  json={"chat_id": CHANNEL_ID, "text": full_post, "parse_mode": "HTML"})

if __name__ == "__main__":
    run_bot()
