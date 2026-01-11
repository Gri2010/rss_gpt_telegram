import os
import requests

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

def test_tg():
    # 1. Проверяем самого бота
    url_me = f"https://api.telegram.org/bot{TOKEN}/getMe"
    r_me = requests.get(url_me).json()
    
    if r_me.get("ok"):
        print(f"✅ Бот найден! Его имя: @{r_me['result']['username']}")
    else:
        print(f"❌ ОШИБКА: Телеграм не видит бота. Проверь TELEGRAM_BOT_TOKEN в секретах.")
        print(f"Ответ сервера: {r_me}")
        return

    # 2. Проверяем канал
    url_chat = f"https://api.telegram.org/bot{TOKEN}/getChat?chat_id={CHANNEL_ID}"
    r_chat = requests.get(url_chat).json()
    
    if r_chat.get("ok"):
        print(f"✅ Канал найден! Название: {r_chat['result'].get('title')}")
    else:
        print(f"❌ ОШИБКА: Канал {CHANNEL_ID} не найден.")
        print("1. Проверь TELEGRAM_CHANNEL_ID (должен быть @Biotech_Pulse)")
        print("2. Проверь, что бот добавлен в канал как АДМИНИСТРАТОР.")
        print(f"Ответ сервера: {r_chat}")

if __name__ == "__main__":
    test_tg()
