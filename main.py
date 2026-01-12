import os
import asyncio
from playwright.async_api import async_playwright
import requests
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Секреты
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
            logger.info("Вход на Flowersale...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            
            await asyncio.sleep(10)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(5)

            logger.info("Переход в раздел Planten...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            # Ждем прогрузки таблицы
            await asyncio.sleep(15)

            # --- СБОР ПОСТОВ (Берем данные как есть) ---
            products = await page.evaluate('''() => {
                const results = [];
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€'));
                rows.slice(0, 20).forEach(row => {
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
            
            # --- СКАЧИВАНИЕ ФАЙЛА ---
            price_path = None
            try:
                logger.info("Пробую нажать на принтер...")
                await page.locator('.fa-print').first.click()
                await asyncio.sleep(4)
                
                async with page.expect_download(timeout=45000) as download_info:
                    # Жмем Enter для подтверждения во втором окне
                    await page.keyboard.press("Enter")
                
                download = await download_info.value
                price_path = f"./price_list.pdf"
                await download.save_as(price_path)
            except Exception as e:
                logger.warning(f"Файл не скачался: {e}")

            await browser.close()
            return products, price_path

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await browser.close()
            return [], None

async def main():
    # Проверка связи
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                  json={"chat_id": CHANNEL_ID, "text": "🚀 Бот в работе. Проверяю остатки Planten..."})

    items, price_file = await work_with_florisoft()
    
    if not items:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": CHANNEL_ID, "text": "⚠️ Не удалось собрать товары. Проверьте логи."})
        return

    # Отправляем 5 случайных позиций напрямую
    hot_deals = random.sample(items, min(len(items), 5))
    for item in hot_deals:
        msg = (f"💠 <b>{item['name']}</b>\n\n"
               f"📏 Размер: {item['size']}\n"
               f"💰 Цена: {item['price']}€\n"
               f"📦 В наличии: {item['stock']} шт.")
        
        if item['photo'] and 'http' in item['photo']:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                          json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": msg, "parse_mode": "HTML"})
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
        await asyncio.sleep(2)

    # Если файл скачался — шлем его
    if price_file:
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📄 Актуальный прайс-лист"}, files={"document": f})

if __name__ == "__main__":
    asyncio.run(main())
