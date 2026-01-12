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
            logger.info("Авторизация...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            await asyncio.sleep(10)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(5)

            logger.info("Раздел Planten...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            await asyncio.sleep(12)

            # 1. Собираем посты (это уже работало)
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

            # 2. ПРЯМОЙ ВЫЗОВ ОКНА (Без поиска иконки)
            logger.info("Принудительный вызов окна EXCEL...")
            price_path = None
            try:
                async with page.expect_download(timeout=60000) as download_info:
                    # Мы имитируем нажатие кнопки EXCEL через JavaScript, 
                    # посылая событие сразу в систему Florisoft
                    await page.evaluate('''() => {
                        // Пытаемся найти кнопку EXCEL по тексту во всем документе
                        const btns = Array.from(document.querySelectorAll('button, a, div, span'));
                        const excel = btns.find(b => b.innerText && b.innerText.includes('EXCEL'));
                        if (excel) {
                            excel.click();
                        } else {
                            // Если окна еще нет, пробуем вызвать сам метод печати (часто это ExportToExcel)
                            if (window.ExportToExcel) window.ExportToExcel();
                            // Или просто жмем на иконку принтера через JS
                            document.querySelector('.fa-print')?.parentElement?.click();
                        }
                    }''')
                    
                    # Если окно "Печатная продукция" появилось, жмем на EXCEL еще раз
                    await asyncio.sleep(3)
                    await page.evaluate('''() => {
                        const excel = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('EXCEL'));
                        if (excel) excel.click();
                    }''')
                
                download = await download_info.value
                price_path = f"./price_list.xlsx"
                await download.save_as(price_path)
                logger.info("Победа! Файл скачан.")
            except Exception as e:
                logger.warning(f"Excel не скачан, но посты сейчас отправим. Ошибка: {e}")

            await browser.close()
            return products, price_path

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await browser.close()
            return [], None

async def main():
    items, price_file = await work_with_florisoft()
    
    # 1. Шлем посты
    if items:
        selected = random.sample(items, min(len(items), 5))
        for item in selected:
            msg = f"🌿 <b>{item['name']}</b>\n📏 {item['size']}\n💰 {item['price']}€\n📦 {item['stock']} шт."
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
            await asyncio.sleep(2)

    # 2. Шлем файл
    if price_file:
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📊 Прайс Planten"}, files={"document": f})

if __name__ == "__main__":
    asyncio.run(main())
