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
GROQ_KEY = os.getenv('GROQ_API_KEY')
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

            logger.info("Переход в раздел...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            # Ждем, пока таблица и зеленая полоса точно появятся
            await page.wait_for_selector('tr', timeout=30000)
            await asyncio.sleep(10)

            # --- ЧАСТЬ 1: Собираем данные для постов ---
            products = await page.evaluate('''() => {
                const results = [];
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€'));
                rows.slice(0, 40).forEach(row => {
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

            # --- ЧАСТЬ 2: Жмем на принтер через JS (самый надежный метод) ---
            logger.info("Пытаюсь нажать на принтер через JS...")
            
            async with page.expect_download(timeout=60000) as download_info:
                # Этот скрипт найдет иконку принтера и принудительно кликнет по её родителю (кнопке)
                await page.evaluate('''() => {
                    const printIcon = document.querySelector('.fa-print');
                    if (printIcon) {
                        printIcon.closest('button').click();
                    } else {
                        // Если нет класса .fa-print, ищем по атрибуту title (часто там написано Print)
                        const printBtn = document.querySelector('[title*="Print"], [title*="print"]');
                        if (printBtn) printBtn.click();
                    }
                }''')
            
            download = await download_info.value
            price_path = f"./{download.suggested_filename}"
            await download.save_as(price_path)
            
            await browser.close()
            return products, price_path

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await page.screenshot(path="error_report.png")
            with open("error_report.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": f"Василий, опять принтер не видит. Ошибка: {e}"}, files={"photo": f})
            await browser.close()
            return [], None

# Функции generate_pitch и main остаются такими же, как в прошлом сообщении
# (Не забудь их оставить в коде!)
