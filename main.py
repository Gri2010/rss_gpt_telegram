import os
import feedparser
import requests
from openai import OpenAI

# 1. ЗАГРУЗКА НАСТРОЕК
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
DEEPSEEK_KEY = os.getenv('DEEPSEEK_KEY')

# 2. ИСТОЧНИКИ НОВОСТЕЙ
FEEDS = [
    "https://www.sciencedaily.com/rss/matter_energy/biotechnology.xml",
    "https://www.nature.com/nbt.rss",
    "https://www.fiercebiotech.com/rss"
]

# 3. ПОДКЛЮЧЕНИЕ К НЕЙРОСЕТИ
client = OpenAI(api_key=DEEPSEEK_KEY, base_url="https://api.deepseek.com/v1")

def run_bot():
    # Загружаем список уже опубликованных ссылок из файла
    if os.path.exists('posted_links.txt'):
        with open('posted_links.txt', 'r') as f:
            posted = f.read().splitlines()
    else:
        posted = []

    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]: # Проверяем 5 последних новостей
            if entry.link not in posted:
                print(f"Обрабатываю: {entry.title}")
                
                # Перевод и саммари через Deepseek
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "Ты научный журналист. Переведи новость на русский, сделай краткое саммари и добавь эмодзи. Хэштеги: #биотех #наука"},
                        {"role": "user", "content": f"{entry.title}\n\n{entry.description}"}
                    ]
                )
                
                text = response.choices[0].message.content
                final_post = f"{text}\n\n🔗 {entry.link}"
                
                # Отправка в Telegram
                send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                requests.post(send_url, data={"chat_id": CHANNEL_ID, "text": final_post})
                
                # Записываем ссылку, чтобы не повторяться
                with open('posted_links.txt', 'a') as f:
                    f.write(entry.link + '\n')
                
                print("Пост отправлен!")
                return # Завершаем работу после одного нового поста за раз

if __name__ == "__main__":
    run_bot()
