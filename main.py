import os
import feedparser
import requests

# ПОПРАВЛЕННЫЕ ИМЕНА ПОД ТВОИ СЕКРЕТЫ
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') # Было TELEGRAM_TOKEN
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID') # Было CHANNEL_ID
GROQ_KEY = os.getenv('GROQ_API_KEY')

FEEDS = ["https://www.nature.com/nbt.rss"]

def ask_ai(text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Ты научный журналист. Переведи заголовок на русский и сделай краткий пересказ в 2-3 предложениях. Добавь эмодзи и хэштеги #биотех #наука"},
            {"role": "user", "content": text}
        ]
    }
    try:
        r = requests.post(url, json=payload, headers=headers)
        return r.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Ошибка нейросети: {e}")
        return None

def run_bot():
    # Проверка базы ссылок
    if os.path.exists('posted_links.txt'):
        with open('posted_links.txt', 'r') as f:
            posted = f.read().splitlines()
    else:
        posted = []
    
    feed = feedparser.parse(FEEDS[0])
    for entry in feed.entries[:3]:
        if entry.link not in posted:
            print(f"Новость найдена: {entry.title}")
            text = ask_ai(entry.title)
            if text:
                msg = f"{text}\n\n🔗 {entry.link}"
                # Отправка
                res = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                  data={"chat_id": CHANNEL_ID, "text": msg})
                
                if res.status_code == 200:
                    with open('posted_links.txt', 'a') as f:
                        f.write(entry.link + '\n')
                    print("УСПЕХ! Сообщение отправлено в канал.")
                    return
                else:
                    print(f"Ошибка Телеграм: {res.text}")
            else:
                print("Не удалось получить текст от нейросети.")

if __name__ == "__main__":
    run_bot()
