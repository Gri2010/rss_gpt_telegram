import os
import requests
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Секреты
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')
FLORI_COOKIES = os.getenv('FLORI_COOKIES')

def get_real_stock():
    """
    Функция для связи с Florisoft.
    Пока мы настраиваем парсинг, она будет брать случайный товар,
    но использовать твои заголовки для будущих запросов.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'Cookie': FLORI_COOKIES,
        'Accept': 'application/json'
    }
    
    # Ссылка на раздел с растениями из твоего cURL
    url = "https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148"
    
    # ВНИМАНИЕ: Здесь мы позже напишем логику вытягивания таблицы.
    # Сейчас просто имитируем успешный заход.
    logger.info("Попытка имитации входа на Florisoft...")
    
    # Для теста оставим список реальных позиций, которые ты обычно там видишь
    # (Замени их на те, что сейчас в наличии!)
    real_items = [
        {"name": "Ficus Lyrata", "price": "14.50", "size": "17/60", "stock": "45"},
        {"name": "Monstera Deliciosa", "price": "12.80", "size": "15/50", "stock": "120"},
        {"name": "Alocasia Polly", "price": "9.20", "size": "12/30", "stock": "80"}
    ]
    return random.choice(real_items)

def generate_pitch(item):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        f"Ты - байер. Сделай краткое предложение по лоту: {item['name']}. "
        f"Цена: {item['price']} евро. Параметры: {item['size']}. Остаток: {item['stock']} шт. "
        "Пиши только по делу: название, ТТХ, цена, краткий прогноз (ликвидность). "
        "Используй HTML: <b>, <i>. Никакой воды."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": prompt}],
        "temperature": 0.3
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🔥 <b>{item['name']}</b> ({item['size']}) по цене {item['price']}€"

def run_bot():
    item = get_real_stock()
    pitch = generate_pitch(item)
    
    full_post = (
        f"💹 <b>STOCK UPDATE: Florisoft</b>\n"
        f"────────────────────\n\n"
        f"{pitch}\n\n"
        f"────────────────────\n"
        f"🚛 <i>Доступно для заказа в панели Florisoft</i>\n"
        f"#Опт #Горшечные #Закупки"
    )

    send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(send_url, json={"chat_id": CHANNEL_ID, "text": full_post, "parse_mode": "HTML"})

if __name__ == "__main__":
    run_bot()
