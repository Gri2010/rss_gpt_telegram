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
            await asyncio.sleep(12)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(5)

            logger.info("Переход в Planten...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            
            # Вместо строгого ожидания просто даем Blazor 15 секунд прогрузить таблицу
            await asyncio.sleep(15) 

            # --- ЧАСТЬ 1: СБОР ДАННЫХ ДЛЯ ПОСТОВ ---
            logger.info("Собираю данные для постов...")
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
            
            logger.info(f"Собрано для постов: {len(products)}")

            # --- ЧАСТЬ 2: РАБОТА С ПРИНТЕРОМ И ВТОРЫМ ОКНОМ ---
            logger.info("Жму на принтер и ищу второе окно...")
            price_path = None
            try:
                # 1. Жмем на принтер на зеленой полосе
                await page.locator('.fa-print').first.click()
                await asyncio.sleep(5) # Ждем появления второго окна

                # 2. Ловим скачивание и жмем на ЛЮБУЮ кнопку во втором окне (Download/OK/Export)
                async with page.expect_download(timeout=60000) as download_info:
                    await page.evaluate('''() => {
                        // Ищем кнопки, которые часто бывают в поп-апах экспорта
                        const selectors = ['button:not([disabled])', 'a.btn', '.modal-footer button'];
                        for (let s of selectors) {
                            const elements = document.querySelectorAll(s);
                            for (let el of elements) {
                                if (/Download|OK|Export|Print|Скачать|Принять/i.test(el.innerText)) {
                                    el.click();
                                    return;
                                }
                            }
                        }
                    }''')
                download = await download_info.value
                price_path = f"./{download.suggested_filename}"
                await download.save_as(price_path)
                logger.info("Файл скачан успешно!")
            except Exception as e:
                logger.warning(f"Не удалось скачать файл через второе окно: {e}")
                # Делаем скриншот этого второго окна для диагностики
                await page.screenshot(path="popup_debug.png")
                with open("popup_debug.png", "rb") as f:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                                  data={"chat_id": CHANNEL_ID, "caption": "Вась, посмотри на это окно. Что тут нажать?"}, files={"photo": f})

            await browser.close()
            return products, price_path

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            await browser.close()
            return [], None

# Функции generate_pitch и main остаются те же (убедись, что они в конце файла)
