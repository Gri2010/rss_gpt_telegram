import os
import feedparser
import requests

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

FEEDS = ["https://www.nature.com/nbt.rss"]

def ask_ai(text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Ты научный журналист. Переведи заголовок на русский и сделай краткое резюме (2 предложения). Добавь эмодзи."},
            {"role": "user", "content": text}
        ]
    }
    try:
        r = requests.post(url, json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except:
        return None

def run_bot():
    # Очистка истории для теста (потом можно убрать)
    posted = open('posted_links.txt', 'r').read().splitlines() if os.path.exists('posted_links.txt') else []
    
    feed = feedparser.parse(FEEDS[0])
    for entry in feed.entries[:3]:
        if entry.link not in posted:
            print(f"Попытка отправить: {entry.title}")
            text = ask_ai(entry.title)
            if text:
                msg = f"{text}\n\n🔗 {entry.link}"
                res = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                  data={"chat_id": CHANNEL_ID, "text": msg})
                
                if res.status_code == 200:
                    with open('posted_links.txt', 'a') as f:
                        f.write(entry.link + '\n')
                    print("УСПЕХ! Пост в канале.")
                    return
                else:
                    print(f"Ошибка ТГ: {res.text}")

if __name__ == "__main__":
    run_bot()
