import os
import feedparser
import requests
import google.generativeai as genai

# 1. НАСТРОЙКИ (берутся из Secrets)
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# Ленты новостей
FEEDS = [
    "https://www.sciencedaily.com/rss/matter_energy/biotechnology.xml",
    "https://www.nature.com/nbt.rss",
    "https://www.fiercebiotech.com/rss"
]

# 2. ПОДКЛЮЧЕНИЕ К GEMINI
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def run_bot():
    # Проверка списка уже опубликованных ссылок
    if os.path.exists('posted_links.txt'):
        with open('posted_links.txt', 'r') as f:
            posted = f.read().splitlines()
    else:
        posted = []

    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            if entry.link not in posted:
                print(f"Обработка: {entry.title}")
                
                prompt = f"Ты научный журналист. Переведи на русский, сделай саммари (3 предложения) и добавь эмодзи. Хэштеги: #биотех #наука. Текст: {entry.title}"
                
                try:
                    response = model.generate_content(prompt)
                    if not response.text:
                        continue
                    text = response.text
                except Exception as e:
                    print(f"Ошибка Gemini: {e}")
                    continue

                final_post = f"{text}\n\n🔗 Источник: {entry.link}"
                
                # Отправка в Telegram
                send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                r = requests.post(send_url, data={"chat_id": CHANNEL_ID, "text": final_post})
                
                if r.status_code == 200:
                    with open('posted_links.txt', 'a') as f:
                        f.write(entry.link + '\n')
                    print("Успех! Пост в канале.")
                    return # Постим по одной за раз
                else:
                    print(f"Ошибка ТГ: {r.text}")

if __name__ == "__main__":
    run_bot()
