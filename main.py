import os
import feedparser
import requests
import google.generativeai as genai

# 1. НАСТРОЙКИ
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

FEEDS = [
    "https://www.sciencedaily.com/rss/matter_energy/biotechnology.xml",
    "https://www.nature.com/nbt.rss",
    "https://www.fiercebiotech.com/rss"
]

# 2. ПОДКЛЮЧЕНИЕ К GEMINI
genai.configure(api_key=GEMINI_KEY)

# Пробуем модель gemini-pro (она самая универсальная для старых библиотек)
model = genai.GenerativeModel('gemini-pro')

def run_bot():
    if os.path.exists('posted_links.txt'):
        with open('posted_links.txt', 'r') as f:
            posted = f.read().splitlines()
    else:
        posted = []

    for url in FEEDS:
        feed = feedparser.parse(url)
        if not feed.entries:
            continue
            
        for entry in feed.entries[:5]:
            if entry.link not in posted:
                print(f"Новость найдена: {entry.title}")
                
                prompt = f"Ты научный журналист. Переведи новость на русский, сделай саммари (3 предложения) и добавь эмодзи. Хэштеги: #биотех #наука. Текст: {entry.title}"
                
                try:
                    # Пытаемся сгенерировать текст
                    response = model.generate_content(prompt)
                    text = response.text
                except Exception as e:
                    print(f"Ошибка Gemini (модель pro): {e}")
                    # Если не вышло, пробуем еще раз с 1.5-flash без лишних слов
                    try:
                        temp_model = genai.GenerativeModel('gemini-1.5-flash')
                        response = temp_model.generate_content(prompt)
                        text = response.text
                    except Exception as e2:
                        print(f"Ошибка Gemini (модель flash): {e2}")
                        continue

                final_post = f"{text}\n\n🔗 Источник: {entry.link}"
                
                # Отправка в Telegram
                send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                payload = {"chat_id": CHANNEL_ID, "text": final_post}
                r = requests.post(send_url, data=payload)
                
                if r.status_code == 200:
                    with open('posted_links.txt', 'a') as f:
                        f.write(entry.link + '\n')
                    print("Опубликовано!")
                    return 
                else:
                    print(f"Ошибка Телеграм: {r.text}")

if __name__ == "__main__":
    run_bot()
