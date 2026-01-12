import os
import asyncio
from playwright.async_api import async_playwright
import requests
import re

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
FLORI_USER = os.getenv('FLORI_USER')
FLORI_PASS = os.getenv('FLORI_PASS')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Логин (проверенный этап)
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            await asyncio.sleep(12)
            await page.keyboard.press("Enter")
            await asyncio.sleep(5)

            # 2. Прямой запрос данных
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/ALL___")
            await asyncio.sleep(5)
            
            raw_html = await page.evaluate('''async () => {
                const res = await fetch('https://flosal.florisoft-cloud.com/Voorraad/Section/items?itemCount=20&columnCount=1&Groep=PLANT_&Voorcod=PLANT&Celcod=ALL___');
                return await res.text();
            }''')

            # 3. Отправляем кусок кода в ТГ для анализа
            # Мы берем 1000 символов из середины, где обычно лежат товары
            sample = raw_html[5000:7000] 
            debug_msg = f"🔍 СТРУКТУРА ДАННЫХ:\n\n<code>{sample.replace('<', '&lt;').replace('>', '&gt;')}</code>"
            
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": debug_msg, "parse_mode": "HTML"})

        except Exception as e:
            print(f"Ошибка: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
