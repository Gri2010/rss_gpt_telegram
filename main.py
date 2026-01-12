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

async def download_full_price():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Устанавливаем большой экран, чтобы все кнопки были видны
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. Заходим и логинимся
            logger.info("Захожу на Flowersale...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await asyncio.sleep(5)
            
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            await asyncio.sleep(8)
            await page.keyboard.press("Enter") # Пробиваем выбор склада
            
            # 2. Переход в "Горшечные" (как на твоем скриншоте)
            logger.info("Нажимаю на 'Горшечные'...")
            await page.click('text="Горшечные"')
            await asyncio.sleep(5)
            
            # 3. Нажимаем "Все группы" слева
            logger.info("Выбираю 'Все группы'...")
            await page.click('.tree-node-content:has-text("Все группы")')
            await asyncio.sleep(5)

            # 4. Скачивание прайса через кнопку Принтера
            logger.info("Нажимаю на значок принтера для скачивания...")
            
            # Ожидаем событие загрузки файла после клика
            async with page.expect_download() as download_info:
                # Ищем иконку принтера (обычно это .fa-print или кнопка с этим классом)
                await page.locator('.fa-print, .print-button, [title*="print"]').first.click()
            
            download = await download_info.value
            file_path = f"./{download.suggested_filename}"
            await download.save_as(file_path)
            
            logger.info(f"Файл успешно скачан: {file_path}")
            await browser.close()
            return file_path

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await page.screenshot(path="path_error.png")
            # Шлем скриншот, чтобы понять, на каком этапе кнопка не нажалась
            with open("path_error.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": f"Не смог нажать: {e}"}, files={"photo": f})
            await browser.close()
            return None

async def main():
    price_file = await download_full_price()
    
    if price_file:
        # Отправляем именно тот файл, который отдал сайт
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📦 Свежий полный прайс (Горшечные)"}, 
                          files={"document": f})
        # Удаляем временный файл
        os.remove(price_file)
    else:
        logger.error("Файл не был получен.")

if __name__ == "__main__":
    asyncio.run(main())
