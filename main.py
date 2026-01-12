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
        # Эмулируем реальный браузер
        context = await browser.new_context(viewport={'width': 1280, 'height': 800}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()
        
        try:
            logger.info("Захожу на страницу логина...")
            await page.goto("https://flosal.florisoft-cloud.com/login", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)

            # Ввод логина и пароля
            logger.info("Ввожу данные авторизации...")
            await page.fill('input[type="email"], input[name*="user"], input[id*="username"]', str(FLORI_USER))
            await page.fill('input[type="password"]', str(FLORI_PASS))
            await page.keyboard.press("Enter")
            
            # Ждем перехода
            await asyncio.sleep(10)

            # Если после логина есть кнопка выбора склада/компании - жмем Enter
            if "select" in page.url.lower() or "selection" in page.url.lower():
                await page.keyboard.press("Enter")
                await asyncio.sleep(5)

            logger.info("Перехожу к прайсу...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148", timeout=60000)
            await asyncio.sleep(10)

            # Скроллим для подгрузки данных
            for _ in range(10):
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(1)

            # Сбор данных
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
            unique = {p['name'] + p['size']: p for p in products if len(p['name']) > 2}.values()
            return list(unique)

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await page.screenshot(path="error_flori.png")
            with open("error_flori.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": f"❌ Ошибка входа: {e}"}, files={"photo": f})
            await browser.close()
            return []

def save_to_csv(items):
    filename = "florisoft_price.csv"
    if not items: return None
    keys = items[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(items)
    return filename

def generate_pitch(item):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = f"Краткий оффер: {item['name']}, {item['size']}, цена {item['price']}. Используй HTML <b>. Пиши по-русски."
    try:
        res = requests.post(url, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}, headers=headers, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🌿 <b>{item['name']}</b> ({item['size']}) — {item['price']}€"

async def main():
    items = await get_full_stock()
    if not items:
        return

    csv_file = save_to_csv(items)
    hot_deals = random.sample(items, min(len(items), 5))
    
    # 1. Постим 5 случайных товаров
    for item in hot_deals:
        pitch = generate_pitch(item)
        caption = f"🔥 <b>TOP OFFER</b>\n\n{pitch}\n\n📍 Склад: {item['stock']} шт."
        if item['photo'] and 'http' in item['photo']:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": caption, "parse_mode": "HTML"})
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"})

    # 2. Постим файл со всем прайсом
    if csv_file:
        with open(csv_file, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": f"📄 Полный прайс Florisoft\nПозиций: {len(items)}"}, files={"document": f})

if __name__ == "__main__":
    asyncio.run(main())
