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
    # Пытаемся по очереди разные варианты написания модели
    # Это решает проблему 404 в разных регионах
    variants = [
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
        "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    ]
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Ты научный журналист. Переведи на русский и сделай краткое резюме (3 предложения): {text}"}]
        }]
    }
    
    for url in variants:
        try:
            full_url = f"{url}?key={GEMINI_KEY}"
            response = requests.post(full_url, json=payload, timeout=10)
            data = response.json()
            
            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                print(f"Попытка через {url} не удалась: {data.get('error', {}).get('message', 'Unknown error')}")
        except Exception as e:
            print(f"Ошибка сети для {url}: {e}")
            continue
            
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
                    res = requests.post(send_url, data={"chat_id": CHANNEL_ID, "text": final_post})
                    
                    if res.status_code == 200:
                        with open('posted_links.txt', 'a') as f:
                            f.write(entry.link + '\n')
                        print("УСПЕХ! Пост в канале.")
                        return
                    else:
                        print(f"Ошибка ТГ: {res.text}")
                else:
                    print("Ни одна модель Gemini не ответила.")

if __name__ == "__main__":
    run_bot()
