import os
import feedparser
import requests
from google import genai

# 1. НАСТРОЙКИ
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

FEEDS = [
    "https://www.sciencedaily.com/rss/matter_energy/biotechnology.xml",
    "https://www.nature.com/nbt.rss",
    "https://www.fiercebiotech.com/rss"
]

# 2. ПОДКЛЮЧЕНИЕ К GEMINI (Новый способ)
client = genai.Client(api_key=GEMINI_KEY)

def run_bot():
    if os.path.exists('posted_links.txt'):
        with open('posted_links.txt', 'r') as f:
            posted = f.read().splitlines()
    else:
        posted = []

    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            if entry.link not in posted:
                print(f"Новость найдена: {entry.title}")
                
                prompt = f"Ты научный журналист. Переведи новость на русский, сделай краткое резюме (3 предложения) и добавь эмодзи. Хэштеги: #биотех #наука. Текст: {entry.title} - {entry.description}"
                
                try:
                    # Новый формат вызова модели
                    response = client.models.generate_content(
                        model="gemini-1.5-flash", 
                        contents=prompt
                    )
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
                    print("Опубликовано!")
                    return 
                else:
                    print(f"Ошибка Телеграм: {r.text}")

if __name__ == "__main__":
    run_bot()
