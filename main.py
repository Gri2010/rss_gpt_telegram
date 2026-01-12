import os
import requests
import random
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем секреты
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

def get_random_plant_id():
    """Ищет случайное растение через API POWO с имитацией браузера"""
    seeds = ["sub", "fl", "bi", "tri", "mon", "per", "gra", "ros", "al", "phy", "oxy", "mega"]
    query = random.choice(seeds)
    
    # Добавляем заголовки, чтобы сервер думал, что заходит обычный человек через Chrome
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    url = f"https://powo.science.kew.org/api/2/search?q={query}&perPage=50"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get('results'):
            # Фильтруем принятые названия
            valid_plants = [p for p in data['results'] if p.get('accepted')]
            return random.choice(valid_plants) if valid_plants else data['results'][0]
    except Exception as e:
        logger.error(f"Ошибка при поиске в POWO: {e}")
    return None

def analyze_with_ai(plant_data):
    """Генерирует пост на основе реальных данных без выдумок"""
    name = plant_data.get('name')
    family = plant_data.get('family', 'Неизвестно')
    author = plant_data.get('author', '')
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = (
        "Ты — эксперт-ботаник. Твоя задача — описать растение строго на основе фактов. "
        "Инструкция: "
        "1. Укажи официальное русское название. Если его нет — дай точную кириллическую транскрипцию латинского названия. "
        "2. Опиши естественную среду обитания (регион, климат). "
        "3. Обязательно разбери: возможно ли выращивание в домашних условиях или в саду в РФ. Если да — краткие условия, если нет — объясни почему (нужна оранжерея, специфическая почва и т.д.). "
        "4. Укажи практическое применение (медицина, биотех, декор) только если это подтвержденный факт. "
        "Никакой выдуманной информации. Стиль научный, но понятный. Используй HTML: <b>, <i>."
    )
    
    user_content = f"Латынь: {name}. Семейство: {family}. Автор: {author}."
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.3
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"Ошибка Groq AI: {e}")
        return f"Новый объект в базе: <b>{name}</b> (Семейство: {family})."

def run_bot():
    logger.info("🌿 Поиск реальных данных в архивах Kew Gardens (с обходом блокировки)...")
    
    plant = get_random_plant_id()
    if not plant:
        logger.error("Не удалось получить данные от POWO API (вероятно, блокировка по IP или User-Agent)")
        return

    ai_text = analyze_with_ai(plant)
    
    fqId = plant.get('fqId')
    powo_link = f"https://powo.science.kew.org/taxon/{fqId}"
    
    full_post = (
        f"📖 <b>Ботаническое досье: {plant.get('name')}</b>\n"
        f"────────────────────\n\n"
        f"{ai_text}\n\n"
        f"────────────────────\n"
        f"🔗 <a href='{powo_link}'>Карточка вида в POWO</a>\n\n"
        f"#Ботаника #KewGardens #ДомашниеРастения"
    )

    send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(send_url, json={
            "chat_id": CHANNEL_ID,
            "text": full_post,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        })
        if res.status_code == 200:
            logger.info(f"✅ Данные о {plant.get('name')} успешно опубликованы.")
        else:
            logger.error(f"Ошибка ТГ: {res.text}")
    except Exception as e:
        logger.error(f"Ошибка при отправке: {e}")

if __name__ == "__main__":
    run_bot()
