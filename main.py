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

async def work_with_florisoft():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            logger.info("Вход в систему...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            await asyncio.sleep(10)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(5)

            # Переход в Planten
            logger.info("Переход в Planten...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            await asyncio.sleep(10)

            # 1. Собираем данные для постов прямо из таблицы (пока открыта страница)
            products = await page.evaluate('''() => {
                const results = [];
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€'));
                rows.slice(0, 15).forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length >= 5) {
                        results.push({
                            name: cells[1]?.innerText.trim(),
                            size: cells[2]?.innerText.trim(),
                            stock: cells[3]?.innerText.trim(),
                            price: cells[4]?.innerText.trim(),
                            photo: row.querySelector('img')?.src || null
                        });
                    }
                });
                return results;
            }''')

            # 2. Жмем на принтер, чтобы вызвать окно "Печатная продукция"
            logger.info("Вызываю окно печати...")
            await page.locator('.fa-print').first.click()
            await asyncio.sleep(5)

            # 3. Жмем на кнопку EXCEL в появившемся окне
            logger.info("Жму на кнопку EXCEL...")
            price_path = None
            try:
                async with page.expect_download(timeout=60000) as download_info:
                    # Ищем кнопку, которая содержит текст EXCEL (как на твоем скрине)
                    await page.get_by_text("EXCEL").first.click()
                
                download = await download_download_info.value
                price_path = f"./flowersale_price.xlsx"
                await download.save_as(price_path)
                logger.info("Файл Excel успешно получен!")
            except Exception as e:
                logger.error(f"Не удалось нажать на EXCEL: {e}")

            await browser.close()
            return products, price_path

        except Exception as e:
            logger.error(f"Общий сбой: {e}")
            await browser.close()
            return [], None

async def main():
    items, price_file = await work_with_florisoft()
    
    # Сначала отправляем посты
    if items:
        selected = random.sample(items, min(len(items), 5))
        for item in selected:
            msg = f"🌿 <b>{item['name']}</b>\n📏 {item['size']}\n💰 {item['price']}€\n📦 Склад: {item['stock']}"
            if item['photo'] and 'http' in item['photo']:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": msg, "parse_mode": "HTML"})
            else:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
            await asyncio.sleep(2)

    # Затем отправляем файл Excel
    if price_file:
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📊 Полный прайс-лист (Excel)"}, files={"document": f})
        os.remove(price_file)

if __name__ == "__main__":
    asyncio.run(main())
