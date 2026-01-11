import os
import feedparser
import requests

# 1. НАСТРОЙКИ
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

FEEDS = [
    "https://www.sciencedaily.com/rss/matter_energy/biotechnology.xml",
    "https://www.nature.com/nbt.rss",
    "https://www.fiercebiotech.com/rss"
]

def ask_gemini(text):
    # Прямой запрос к Google API без лишних библиотек
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    payload = {
        "contents": [{
            "parts": [{"text": f"Ты научный журналист. Переведи на русский и сделай краткое резюме (3 предложения): {text}"}]
        }]
    }
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "candidates" in data:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    else:
        print(f"Ошибка Gemini: {data}")
        return None

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
                print(f"Нашел новость: {entry.title}")
                
                translated_text = ask_gemini(entry.title)
                
                if translated_text:
                    final_post = f"{translated_text}\n\n🔗 {entry.link}"
                    send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                    requests.post(send_url, data={"chat_id": CHANNEL_ID, "text": final_post})
                    
                    with open('posted_links.txt', 'a') as f:
                        f.write(entry.link + '\n')
                    print("Опубликовано!")
                    return

if __name__ == "__main__":
    run_bot()
