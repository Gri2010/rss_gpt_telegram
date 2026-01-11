import os
import feedparser
import requests

# Настройки из GitHub Secrets
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

FEEDS = ["https://www.nature.com/nbt.rss"]

def ask_ai(text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Переведи заголовок на русский и сделай краткий пересказ в 2 предложениях. Добавь эмодзи и хэштеги #биотех #наука"},
            {"role": "user", "content": text}
        ]
    }
    try:
        r = requests.post(url, json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except:
        return None

def run_bot():
    # Проверка базы ссылок, чтобы не повторяться
    posted = open('posted_links.txt', 'r').read().splitlines() if os.path.exists('posted_links.txt') else []
    
    feed = feedparser.parse(FEEDS[0])
    for entry in feed.entries[:3]:
        if entry.link not in posted:
            print(f"Новость: {entry.title}")
            text = ask_ai(entry.title)
            if text:
                msg = f"{text}\n\n🔗 {entry.link}"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                              data={"chat_id": CHANNEL_ID, "text": msg})
                with open('posted_links.txt', 'a') as f:
                    f.write(entry.link + '\n')
                print("Запостил!")
                return

if __name__ == "__main__":
    run_bot()
