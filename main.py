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
    # МЕНЯЕМ v1beta на v1 и убираем лишние префиксы
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{"text": f"Ты научный журналист. Переведи на русский и сделай краткое резюме (3 предложения): {text}"}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload)
        data = response.json()
        
        # Если всё равно 404, пробуем альтернативный URL
        if response.status_code == 404:
            url_alt = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_KEY}"
            response = requests.post(url_alt, json=payload)
            data = response.json()

        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"Ответ от Google: {data}")
            return None
    except Exception as e:
        print(f"Ошибка сети: {e}")
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
                        print("Опубликовано!")
                        return
                    else:
                        print(f"Ошибка ТГ: {res.text}")

if __name__ == "__main__":
    run_bot()
