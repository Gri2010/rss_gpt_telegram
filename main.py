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
            # 1. Логин (проверенный путь)
            logger.info("Захожу на сайт...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            
            await page.wait_for_selector('input[placeholder*="Gebruiker"]', timeout=30000)
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            
            await asyncio.sleep(10)
            await page.keyboard.press("Enter") # Склад
            await asyncio.sleep(5)

            # 2. Жмем на ВКЛАДКУ "Горшечные" в верхнем меню
            logger.info("Жму на верхнюю вкладку 'Горшечные'...")
            # Ищем элемент li или a, который содержит текст "Горшечные" в навигации
            await page.locator('nav, .navbar, .menu, .tabs').get_by_text("Горшечные").click()
            await asyncio.sleep(7)

            # 3. Слева выбираем "Все группы"
            logger.info("Выбираю 'Все группы' в боковом меню...")
            await page.locator('.tree-node-content, .sidebar').get_by_text("Все группы").first.click()
            await asyncio.sleep(5)

            # 4. Скачивание через принтер
            logger.info("Ищу кнопку принтера...")
            async with page.expect_download() as download_info:
                # Пробуем нажать на иконку принтера по классу или родителю
                await page.locator('i.fa-print, .btn-print, [title*="print"]').first.click()
            
            download = await download_info.value
            file_path = f"./flowersale_price.pdf" # Обычно принтер отдает PDF или Excel
            await download.save_as(file_path)
            
            logger.info("Файл скачан!")
            await browser.close()
            return file_path

        except Exception as e:
            logger.error(f"Косяк на этапе: {e}")
            await page.screenshot(path="step_error.png")
            with open("step_error.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": f"Василий, глянь скриншот. Застрял тут: {e}"}, files={"photo": f})
            await browser.close()
            return None

async def main():
    price_file = await download_full_price()
    if price_file:
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📄 Твой прайс готов!"}, files={"document": f})
        os.remove(price_file)

if __name__ == "__main__":
    asyncio.run(main())
