import os
import asyncio
from playwright.async_api import async_playwright
import requests

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

async def test_run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Проверка связи: захожу на Google...")
            await page.goto("https://google.com")
            await page.screenshot(path="test.png")
            
            with open("test.png", "rb") as f:
                r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": "✅ Бот работает, скриншот отправлен!"}, 
                              files={"photo": f})
            print(f"Ответ Telegram: {r.status_code}")
        except Exception as e:
            print(f"Ошибка: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_run())
