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
            logger.info("Захожу на flowersale.nl...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle", timeout=60000)
            
            logger.info("Кликаю Login Webshop...")
            await page.get_by_text("Login Webshop").first.click()
            await asyncio.sleep(5)

            logger.info("Авторизация...")
            await page.wait_for_selector('input', timeout=30000)
            # Вводим данные в поля (используем плейсхолдеры, которые мы видели на скрине)
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            
            await asyncio.sleep(10)
            await page.keyboard.press("Enter") # Пробиваем выбор склада

            logger.info("Переход в раздел растений...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148", wait_until="networkidle")
            await asyncio.sleep(12) # Blazor долго подгружает таблицу

            # Глубокий скролл для загрузки всех строк
            for _ in range(10):
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(1.5)

            logger.info("Парсинг таблицы...")
            products = await page.evaluate('''() => {
                const results = [];
                // Ищем все строки, где есть символ евро или цена с запятой
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€') || /[0-9],[0-9]/.test(r.innerText));
                
                rows.forEach(row => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length >= 4) {
                        const img = row.querySelector('img');
                        // Пробуем разные индексы ячеек, так как структура может прыгать
                        results.push({
                            name: cells[1] ? cells[1].innerText.trim() : "Unknown",
                            size: cells[2] ? cells[2].innerText.trim() : "",
                            stock: cells[3] ? cells[3].innerText.trim() : "0",
                            price: cells[4] ? cells[4].innerText.trim() : "0",
                            photo: img ? img.src : null
                        });
                    }
                });
                return results;
            }''')
            
            await browser.close()
            # Убираем дубликаты и слишком короткие названия
            unique = {p['name'] + p['size']: p for p in products if len(p['name']) > 3}.values()
            return list(unique)

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await page.screenshot(path="final_error.png")
            with open("final_error.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": f"Ошибка на этапе сбора: {e}"}, files={"photo": f})
            await browser.close()
            return []

def save_to_csv(items):
    filename = "flowersale_price.csv"
    if not items: return None
    keys = ["name", "size", "stock", "price", "photo"]
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(items)
    return filename

def generate_pitch(item):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = f"Напиши 1 предложение для: {item['name']}, {item['size']}, цена {item['price']}. Используй <b>."
    try:
        res = requests.post(url, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}, headers=headers, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🌿 <b>{item['name']}</b> ({item['size']}) — {item['price']}€"

async def main():
    items = await get_full_stock()
    if not items:
        logger.error("Товары не найдены в таблице.")
        return

    logger.info(f"Найдено товаров: {len(items)}. Отправляю...")
    csv_file = save_to_csv(items)
    
    # Постим 5 штук
    hot_deals = random.sample(items, min(len(items), 5))
    for item in hot_deals:
        pitch = generate_pitch(item)
        caption = f"💹 <b>STOCK UPDATE</b>\n\n{pitch}\n\n📍 В наличии: {item['stock']}"
        if item['photo'] and 'http' in item['photo']:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": caption, "parse_mode": "HTML"})
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"})

    if csv_file:
        with open(csv_file, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": f"📄 Полный прайс ({len(items)} поз.)"}, files={"document": f})

if __name__ == "__main__":
    asyncio.run(main())
