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
GROQ_KEY = os.getenv('GROQ_API_KEY')
FLORI_USER = os.getenv('FLORI_USER')
FLORI_PASS = os.getenv('FLORI_PASS')

async def get_all_stock():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            # 1. Сначала пробуем просто зайти (вдруг пустит)
            logger.info("Пробуем зайти на склад...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148", wait_until="networkidle")
            
            # 2. Если видим форму логина — входим
            if await page.query_selector('input[type="password"]') or "login" in page.url.lower():
                logger.info("Требуется авторизация. Ввожу данные...")
                # Селекторы могут отличаться, обычно это input[type="text"] и input[type="password"]
                await page.fill('input[type="email"], input[name*="user"], input[name*="login"]', FLORI_USER)
                await page.fill('input[type="password"]', FLORI_PASS)
                await page.click('button[type="submit"], input[type="submit"]')
                await page.wait_for_load_state("networkidle")
                # Возвращаемся на страницу склада после логина
                await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            
            await asyncio.sleep(10) # Даем Blazor время прогрузить всё

            # Скроллим до самого низа, чтобы подгрузить ВЕСЬ прайс
            for _ in range(10): 
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(1)

            # Собираем данные
            products = await page.evaluate('''() => {
                const results = [];
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€'));
                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
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
            return products
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await browser.close()
            return []

# ... (функция generate_pitch остается прежней) ...

async def main():
    items = await get_all_stock()
    if not items:
        logger.error("Прайс пуст. Проверь логин/пароль.")
        return

    logger.info(f"Успех! Собрано позиций: {len(items)}")
    
    # Теперь мы можем постить хоть весь прайс, но давай пока оставим 10 штук
    to_post = random.sample(items, min(len(items), 10))

    for i, item in enumerate(to_post):
        # (Тут логика отправки как в прошлом сообщении)
        # ... (пропускаю для краткости, она не меняется)
        pass
