import os
import asyncio
from playwright.async_api import async_playwright
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
FLORI_USER = os.getenv('FLORI_USER')
FLORI_PASS = os.getenv('FLORI_PASS')

async def download_full_price():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. Логин
            logger.info("Захожу на Flowersale...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            
            await page.wait_for_selector('input[placeholder*="Gebruiker"]', timeout=30000)
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            
            await asyncio.sleep(10)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(5)

            # 2. Жмем на вкладку PLANTEN (сверху)
            logger.info("Жму на вкладку 'Planten'...")
            # Ищем именно в верхней навигации
            await page.locator('.nav-link, .menu-item, li').get_by_text("Planten", exact=True).first.click()
            await asyncio.sleep(8)

            # 3. Слева выбираем "Alle groepen"
            logger.info("Выбираю 'Alle groepen'...")
            # Используем фильтр по тексту в левой панели
            await page.get_by_text("Alle groepen").first.click()
            await asyncio.sleep(5)

            # 4. Скачивание через иконку принтера
            logger.info("Скачиваю прайс через иконку принтера...")
            async with page.expect_download() as download_info:
                # В Florisoft иконка принтера часто сидит в кнопке с клазом .fa-print
                await page.locator('.fa-print, [title*="print"], .btn-print').first.click()
            
            download = await download_info.value
            file_path = f"./{download.suggested_filename}"
            await download.save_as(file_path)
            
            logger.info(f"Файл {file_path} успешно получен!")
            await browser.close()
            return file_path

        except Exception as e:
            logger.error(f"Затык: {e}")
            await page.screenshot(path="debug_pl.png")
            with open("debug_pl.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": f"Василий, не нашел Planten: {e}"}, files={"photo": f})
            await browser.close()
            return None

async def main():
    price_file = await download_full_price()
    if price_file:
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📄 Прайс (Planten) обновлен!"}, files={"document": f})
        os.remove(price_file)

if __name__ == "__main__":
    asyncio.run(main())
