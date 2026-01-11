import os
import feedparser
import requests

# Пробуем достать секреты
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

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
    # Проверка на наличие секретов
    if not TOKEN:
        print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не найден в секретах Гитхаба!")
        return
    if not CHANNEL_ID:
        print("❌ ОШИБКА: TELEGRAM_CHANNEL_ID не найден в секретах Гитхаба!")
        return

    print(f"🤖 Бот запущен. Проверяю новости...")
    
    # Чтобы бот точно что-то отправил сейчас, очистим список ссылок для теста
    posted = []
    if os.path.exists('posted_links.txt'):
        with open('posted_links.txt', 'r') as f:
            posted = f.read().splitlines()
    
    feed = feedparser.parse("https://www.nature.com/nbt.rss")
    
    for entry in feed.entries[:3]:
        if entry.link not in posted:
            print(f"📝 Обработка: {entry.title}")
            text = ask_ai(entry.title)
            
            if text:
                msg = f"{text}\n\n🔗 {entry.link}"
                # Прямая отправка
                send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                res = requests.post(send_url, data={"chat_id": CHANNEL_ID, "text": msg})
                
                if res.status_code == 200:
                    with open('posted_links.txt', 'a') as f:
                        f.write(entry.link + '\n')
                    print("✅ ПОБЕДА! Пост отправлен в канал.")
                    return
                else:
                    print(f"❌ Ошибка ТГ: {res.status_code} - {res.text}")
                    print(f"Попытался отправить в: {CHANNEL_ID}")
            else:
                print("❌ Нейросеть не ответила.")

if __name__ == "__main__":
    run_bot()
