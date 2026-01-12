import os
import asyncio
import requests
import random
from groq import Groq

# Секреты из GitHub
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')

client = Groq(api_key=GROQ_KEY)

PLANTS = ["Монстера", "Замиокулькас", "Фикус Лирата", "Сансевиерия", "Спатифиллум", "Алоказия"]

def generate_plant_post(plant_name):
    try:
        # Пробуем модель Llama-3.3-70b (она сейчас самая мощная и стабильная в Groq)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[
                {"role": "system", "content": "Ты крутой блогер-ботаник. Пиши по-русски, интересно и с эмодзи."},
                {"role": "user", "content": f"Напиши пост про комнатное растение {plant_name}: описание, уход (свет/полив) и интересный факт."}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        # Если Groq упал, мы хотим знать ПОЧЕМУ
        return f"DEBUG_ERROR: Ошибка нейронки: {str(e)}"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"})

async def main():
    plant = random.choice(PLANTS)
    post_text = generate_plant_post(plant)
    send_telegram(post_text)

if __name__ == "__main__":
    asyncio.run(main())
