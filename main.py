import os
import asyncio
from playwright.async_api import async_playwright
import requests
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
FLORI_USER = os.getenv('FLORI_USER')
FLORI_PASS = os.getenv('FLORI_PASS')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()

        try:
            logger.info("Вход и получение данных...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            await asyncio.sleep(12)
            await page.keyboard.press("Enter")
            await asyncio.sleep(5)

            # Переходим в раздел, чтобы куки активировались
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/ALL___")
            await asyncio.sleep(5)
            
            # Делаем запрос (itemCount=50 для начала)
            raw_html = await page.evaluate('''async () => {
                const res = await fetch('https://flosal.florisoft-cloud.com/Voorraad/Section/items?itemCount=50&columnCount=1&Groep=PLANT_&Voorcod=PLANT&Celcod=ALL___');
                return await res.text();
            }''')

            # --- ПАРСИНГ ПО ВЕРСТКЕ ---
            # 1. Находим все блоки товаров (li)
            # Мы будем искать названия, цены и ID для фото
            titles = re.findall(r'<h5 class="title">([^<]+)</h5>', raw_html)
            prices = re.findall(r'<span class="bedrag">([^<]+)</span>', raw_html)
            vendors = re.findall(r'<span\s+class="kenmerk-waarde">([^<]+)</span>', raw_html)
            
            # Для фото ищем ID из тега li (например P391507041)
            product_ids = re.findall(r'<li id="(P\d+)"', raw_html)

            logger.info(f"Найдено названий: {len(titles)}, цен: {len(prices)}")

            if titles:
                count = min(5, len(titles))
                for i in range(count):
                    name = titles[i].strip()
                    price = prices[i].strip() if i < len(prices) else "???"
                    vendor = vendors[i].strip() if i < len(vendors) else "Не указан"
                    
                    # Формируем ссылку на фото, если нашли ID
                    # Обычно у них путь такой: /Photos/GetPhoto?id=...
                    photo_url = f"https://flosal.florisoft-cloud.com/Photos/GetPhoto?id={product_ids[i][1:]}" if i < len(product_ids) else None

                    caption = (f"🌿 <b>{name}</b>\n\n"
                               f"🏭 Поставщик: {vendor}\n"
                               f"💰 Цена: {price}€\n"
                               f"📍 Ссылка: <a href='https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/ALL___'>В магазин</a>")

                    # Пробуем отправить с фото, если нет - текстом
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                  json={"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML", "disable_web_page_preview": False})
                    
                    await asyncio.sleep(2)
                
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                              json={"chat_id": CHANNEL_ID, "text": f"✅ Обработка завершена. Всего в прайсе: {len(titles)} позиций."})
            else:
                logger.error("Не удалось извлечь данные. Проверь регулярки.")
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                              json={"chat_id": CHANNEL_ID, "text": "⚠️ Ошибка парсинга: названия не найдены."})

        except Exception as e:
            logger.error(f"Сбой: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
