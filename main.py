import os
import asyncio
from playwright.async_api import async_playwright
import requests
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
FLORI_USER = os.getenv('FLORI_USER')
FLORI_PASS = os.getenv('FLORI_PASS')

async def get_items_via_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 1. Логинимся, чтобы получить живые куки
            logger.info("Авторизация для получения сессии...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            await asyncio.sleep(10)
            await page.keyboard.press("Enter")
            await asyncio.sleep(5)

            # 2. Вытаскиваем куки из браузера
            cookies = await context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            
            # 3. Делаем прямой запрос к API (тот самый cURL)
            # Увеличиваем itemCount, чтобы забрать сразу много позиций (например, 100)
            api_url = "https://flosal.florisoft-cloud.com/Voorraad/Section/items?itemCount=100&columnCount=1&Groep=PLANT_&Voorcod=PLANT&Celcod=ALL___"
            
            headers = {
                'accept': '*/*',
                'cookie': cookie_str,
                'referer': 'https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/ALL___',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
                'x-requested-with': 'XMLHttpRequest'
            }

            logger.info("Запрашиваю данные напрямую из API...")
            response = requests.get(api_url, headers=headers)
            
            if response.status_code == 200:
                # В ответе обычно приходит HTML-кусок с товарами или JSON
                # Мы распарсим его как текст для постов
                return response.text
            else:
                logger.error(f"API ответил ошибкой: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Ошибка API метода: {e}")
            return None
        finally:
            await browser.close()

async def main():
    raw_data = await get_items_via_api()
    
    if raw_data:
        # Поскольку API возвращает HTML-разметку строк, мы просто выдернем названия и цены
        # Это гораздо стабильнее, чем ждать прогрузки всей страницы
        import re
        # Ищем названия (обычно в кавычках или между тегами)
        names = re.findall(r'class="item-name">([^<]+)', raw_data)
        prices = re.findall(r'class="price-value">([^<]+)', raw_data) or re.findall(r'(\d+,\d+)\s*€', raw_data)
        
        if names:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": f"✅ API доступен! Найдено товаров: {len(names)}"})
            
            # Шлем 5 постов
            for i in range(min(5, len(names))):
                price = prices[i] if i < len(prices) else "??"
                msg = f"🌿 <b>{names[i]}</b>\n💰 Цена: {price}€\n📦 Доступно к заказу!"
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                              json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
                await asyncio.sleep(1)
        else:
            # Если регулярка не сработала, пришлем кусок лога в ТГ для отладки
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": f"Данные получены, но не распарсены. Длина: {len(raw_data)}"})
    else:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": CHANNEL_ID, "text": "❌ Не удалось получить данные через API."})

if __name__ == "__main__":
    asyncio.run(main())
