import os
import asyncio
from playwright.async_api import async_playwright
import requests
import random
import logging
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')
FLORI_USER = os.getenv('FLORI_USER')
FLORI_PASS = os.getenv('FLORI_PASS')

async def get_full_stock():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        
        try:
            logger.info("Открываю страницу логина...")
            await page.goto("https://flosal.florisoft-cloud.com/login", wait_until="networkidle", timeout=60000)
            
            # Ждем немного, чтобы JS отработал
            await asyncio.sleep(5)

            # Пробуем найти ЛЮБОЕ поле ввода текста и пароля
            inputs = await page.query_selector_all('input')
            if len(inputs) < 2:
                # Если полей нет, делаем скриншот и шлем в ТГ для диагностики
                await page.screenshot(path="debug.png")
                with open("debug.png", "rb") as f:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                                  data={"chat_id": CHANNEL_ID, "caption": "❌ Не вижу полей логина. Вот что на экране:"},
                                  files={"photo": f})
                raise Exception("Поля логина не найдены на странице")

            logger.info("Ввожу данные...")
            # Заполняем первое попавшееся текстовое поле и поле пароля
            await page.fill('input[type="text"], input[type="email"], input:not([type="password"])', str(FLORI_USER))
            await page.fill('input[type="password"]', str(FLORI_PASS))
            
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)

            logger.info("Перехожу к прайсу...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148", timeout=60000)
            await asyncio.sleep(10)

            # Собираем данные
            products = await page.evaluate('''() => {
                const results = [];
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€'));
                rows.forEach(row => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length >= 5) {
                        const img = row.querySelector('img');
                        results.push({
                            name: cells[1]?.innerText.trim(),
                            size: cells[2]?.innerText.trim(),
                            stock: cells[3]?.innerText.trim(),
                            price: cells[4]?.innerText.trim(),
                            photo: img ? img.src : null
                        });
                    }
                });
                return results;
            }''')
            
            await browser.close()
            return list({p['name'] + p['size']: p for p in products if len(p['name']) > 2}.values())

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await browser.close()
            return []

# Остальные функции (save_to_csv, generate_pitch, main) остаются без изменений
# [Вставь сюда функции из предыдущего кода: save_to_csv, generate_pitch и main]
