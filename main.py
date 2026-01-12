import os
import feedparser
import requests
import random
import time
from datetime import datetime
import json
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загружаем секреты из переменных окружения GitHub
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

# Список источников RSS (биотехнологии растений)
RSS_SOURCES = [
    {
        'name': '🌱 Nature Plants',
        'url': 'https://www.nature.com/nplants.rss',
        'category': 'Научные исследования',
        'language': 'en'
    },
    {
        'name': '🧬 Science Daily - Plants',
        'url': 'https://www.sciencedaily.com/rss/plants_animals/plants.xml',
        'category': 'Новости науки',
        'language': 'en'
    },
    {
        'name': '🔬 Phys.org - Plants',
        'url': 'https://phys.org/rss-feed/biology-news/plants/',
        'category': 'Биологические новости',
        'language': 'en'
    },
    {
        'name': '🌿 Botanichka.ru',
        'url': 'https://botanichka.ru/feed/',
        'category': 'Садоводство',
        'language': 'ru'
    },
    {
        'name': '🧪 Frontiers in Plant Science',
        'url': 'https://www.frontiersin.org/journals/plant-science/articles/rss',
        'category': 'Передовые исследования',
        'language': 'en'
    },
    {
        'name': '🌾 USDA Agricultural Research',
        'url': 'https://www.ars.usda.gov/news/rssfeed/',
        'category': 'Сельское хозяйство',
        'language': 'en'
    },
    {
        'name': '⚗️ Plant Biotechnology Journal',
        'url': 'https://onlinelibrary.wiley.com/rss/journal/14677652',
        'category': 'Биотехнологии',
        'language': 'en'
    },
    {
        'name': '🌳 Биомолекула',
        'url': 'https://biomolecula.ru/rss.xml',
        'category': 'Научпоп на русском',
        'language': 'ru'
    },
    {
        'name': '🌸 Gardeners\' World',
        'url': 'https://www.gardenersworld.com/feed/',
        'category': 'Практическое садоводство',
        'language': 'en'
    }
]

# Файлы для хранения состояния
POSTED_LINKS_FILE = 'posted_links.txt'
SOURCE_ROTATION_FILE = 'source_rotation.json'
LAST_POST_FILE = 'last_post_time.txt'

def load_state():
    """Загружаем состояние бота"""
    state = {
        'posted_links': [],
        'last_source_index': 0,
        'last_post_time': None
    }
    
    # Загружаем опубликованные ссылки
    try:
        if os.path.exists(POSTED_LINKS_FILE):
            with open(POSTED_LINKS_FILE, 'r', encoding='utf-8') as f:
                state['posted_links'] = [line.strip() for line in f.readlines() if line.strip()]
    except Exception as e:
        logger.error(f"Ошибка загрузки ссылок: {e}")
    
    # Загружаем ротацию источников
    try:
        if os.path.exists(SOURCE_ROTATION_FILE):
            with open(SOURCE_ROTATION_FILE, 'r', encoding='utf-8') as f:
                rotation = json.load(f)
                state['last_source_index'] = rotation.get('last_index', 0)
    except Exception as e:
        logger.error(f"Ошибка загрузки ротации: {e}")
    
    return state

def save_state(posted_links, source_index):
    """Сохраняем состояние бота"""
    try:
        # Сохраняем ссылки
        with open(POSTED_LINKS_FILE, 'w', encoding='utf-8') as f:
            for link in posted_links:
                f.write(link + '\n')
        
        # Сохраняем ротацию
        with open(SOURCE_ROTATION_FILE, 'w', encoding='utf-8') as f:
            json.dump({'last_index': source_index}, f, ensure_ascii=False, indent=2)
        
        # Сохраняем время последнего поста
        with open(LAST_POST_FILE, 'w', encoding='utf-8') as f:
            f.write(datetime.now().isoformat())
            
    except Exception as e:
        logger.error(f"Ошибка сохранения состояния: {e}")

def get_next_source(current_index):
    """Получаем следующий источник для публикации"""
    next_index = (current_index + 1) % len(RSS_SOURCES)
    return RSS_SOURCES[next_index], next_index

def analyze_with_ai(title, description, source_name, category):
    """Анализируем новость с помощью Groq AI"""
    if not GROQ_KEY:
        logger.error("GROQ_API_KEY не найден!")
        return None
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }
    
    # Определяем язык промпта
    system_prompt = """Ты эксперт по биотехнологиям растений и научный журналист.
Создай интересный пост для Telegram канала на основе новости.

Пост должен включать:
1. Заголовок на русском с эмодзи
2. Краткое описание новости (3-4 предложения)
3. Практическое значение для садоводов, фермеров или ученых
4. Интересный факт о растении
5. Советы по уходу (если применимо)

Используй живую, доступную речь. Добавь эмодзи для наглядности.
Длина: 300-400 символов."""

    user_content = f"""
Источник: {source_name}
Категория: {category}
Заголовок: {title}
Описание: {description[:500]}
"""
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        logger.info("🤖 Запрашиваю анализ у AI...")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        logger.info("✅ AI анализ получен")
        return content
        
    except Exception as e:
        logger.error(f"❌ Ошибка AI анализа: {e}")
        return None

def fetch_news_from_source(source, max_entries=10):
    """Получаем новости из источника"""
    try:
        logger.info(f"📡 Проверяю источник: {source['name']}")
        feed = feedparser.parse(source['url'])
        
        if not feed.entries:
            logger.warning(f"⚠️ В источнике нет новостей: {source['name']}")
            return []
        
        news_items = []
        for entry in feed.entries[:max_entries]:
            news_item = {
                'title': entry.title if hasattr(entry, 'title') else 'Без заголовка',
                'link': entry.link if hasattr(entry, 'link') else '',
                'description': entry.get('description', '')[:300] if hasattr(entry, 'description') else '',
                'published': entry.get('published', '') if hasattr(entry, 'published') else '',
                'source': source
            }
            news_items.append(news_item)
        
        logger.info(f"✅ Найдено {len(news_items)} новостей из {source['name']}")
        return news_items
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения новостей из {source['name']}: {e}")
        return []

def find_fresh_news(news_items, posted_links):
    """Ищем свежую новость из списка"""
    for news in news_items:
        if news['link'] and news['link'] not in posted_links:
            return news
    return None

def format_telegram_post(news, ai_content):
    """Форматируем пост для Telegram"""
    source = news['source']
    
    # Начинаем формировать пост
    post_parts = []
    
    # Заголовок поста
    post_parts.append(f"<b>{source['name']}</b>\n")
    post_parts.append(f"📌 {source['category']}\n")
    
    # Разделитель
    post_parts.append("─" * 30 + "\n")
    
    # Контент от AI
    if ai_content:
        post_parts.append(ai_content + "\n")
    else:
        # Резервный контент
        post_parts.append(f"📰 {news['title']}\n\n")
        if news['description']:
            post_parts.append(f"{news['description']}\n")
    
    # Разделитель
    post_parts.append("─" * 30 + "\n")
    
    # Источник и ссылка
    post_parts.append(f"🔗 <a href='{news['link']}'>Читать полностью</a>\n")
    
    # Хештеги
    hashtags = ['#Биотехнологии', '#Растения']
    if source['language'] == 'ru':
        hashtags.append('#Наука')
    else:
        hashtags.append('#Science')
    
    if 'садовод' in source['category'].lower():
        hashtags.append('#Садоводство')
    if 'сельск' in source['category'].lower():
        hashtags.append('#Агротехника')
    
    post_parts.append("\n" + " ".join(hashtags))
    
    # Объединяем все части
    full_post = "\n".join(post_parts)
    
    # Проверяем длину
    if len(full_post) > 4000:
        full_post = full_post[:3900] + "...\n\n⚠️ Пост был обрезан"
    
    return full_post

def send_to_telegram(message):
    """Отправляем сообщение в Telegram канал"""
    if not TOKEN or not CHANNEL_ID:
        logger.error("❌ Отсутствуют токены для Telegram!")
        return False
    
    send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    try:
        response = requests.post(
            send_url,
            json={
                "chat_id": CHANNEL_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("✅ Сообщение отправлено в Telegram")
            return True
        else:
            logger.error(f"❌ Ошибка Telegram API: {response.status_code}")
            logger.error(f"Ответ: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки в Telegram: {e}")
        return False

def run_bot():
    """Основная функция бота"""
    logger.info("=" * 50)
    logger.info(f"🌱 ЗАПУСК БОТА ПО БИОТЕХНОЛОГИЯМ РАСТЕНИЙ")
    logger.info(f"🕐 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # Проверяем секреты
    if not all([TOKEN, CHANNEL_ID, GROQ_KEY]):
        logger.error("❌ ОТСУТСТВУЮТ НЕОБХОДИМЫЕ СЕКРЕТЫ!")
        logger.error("Убедитесь, что установлены:")
        logger.error("1. TELEGRAM_BOT_TOKEN")
        logger.error("2. TELEGRAM_CHANNEL_ID")
        logger.error("3. GROQ_API_KEY")
        return
    
    # Загружаем состояние
    state = load_state()
    posted_links = state['posted_links']
    last_source_index = state['last_source_index']
    
    logger.info(f"📊 Состояние: {len(posted_links)} опубликованных ссылок")
    logger.info(f"🎯 Текущий источник: {last_source_index}")
    
    # Получаем следующий источник
    current_source, new_source_index = get_next_source(last_source_index)
    logger.info(f"📰 Выбран источник: {current_source['name']}")
    
    # Получаем новости из источника
    all_news = fetch_news_from_source(current_source, max_entries=15)
    
    if not all_news:
        logger.warning("⚠️ Не удалось получить новости из текущего источника")
        # Пробуем следующий источник
        current_source, new_source_index = get_next_source(new_source_index)
        logger.info(f"🔄 Переключаюсь на: {current_source['name']}")
        all_news = fetch_news_from_source(current_source, max_entries=15)
    
    # Ищем свежую новость
    fresh_news = find_fresh_news(all_news, posted_links)
    
    if not fresh_news:
        logger.warning("⚠️ Нет новых новостей в текущем источнике")
        # Пробуем все остальные источники
        for i in range(len(RSS_SOURCES)):
            temp_source, _ = get_next_source(new_source_index + i)
            if temp_source['name'] != current_source['name']:
                temp_news = fetch_news_from_source(temp_source, max_entries=10)
                fresh_news = find_fresh_news(temp_news, posted_links)
                if fresh_news:
                    current_source = temp_source
                    logger.info(f"🔄 Нашел новость в: {current_source['name']}")
                    break
    
    if not fresh_news:
        logger.error("❌ НЕ НАЙДЕНО НИ ОДНОЙ НОВОЙ НОВОСТИ!")
        # Очищаем историю для теста (если все новости уже опубликованы)
        if len(posted_links) > 50:
            logger.info("🧹 Очищаю историю для теста...")
            posted_links = []
            # Пробуем еще раз
            fresh_news = find_fresh_news(all_news, posted_links)
    
    if not fresh_news:
        logger.error("❌ НЕ УДАЛОСЬ НАЙТИ НОВОСТЬ ДЛЯ ПУБЛИКАЦИИ")
        return
    
    # Анализируем новость через AI
    logger.info(f"📝 Анализирую новость: {fresh_news['title'][:100]}...")
    ai_content = analyze_with_ai(
        fresh_news['title'],
        fresh_news['description'],
        current_source['name'],
        current_source['category']
    )
    
    # Форматируем пост
    telegram_post = format_telegram_post(fresh_news, ai_content)
    
    # Отправляем в Telegram
    logger.info("📤 Отправляю пост в Telegram...")
    if send_to_telegram(telegram_post):
        # Сохраняем состояние
        posted_links.append(fresh_news['link'])
        save_state(posted_links, new_source_index)
        logger.info("✅ ПОСТ УСПЕШНО ОПУБЛИКОВАН!")
        logger.info(f"⏳ Следующая публикация через 1 час")
    else:
        logger.error("❌ НЕ УДАЛОСЬ ОТПРАВИТЬ ПОСТ")

if __name__ == "__main__":
    run_bot()
