import os
import asyncio
from playwright.async_api import async_playwright
import requests
import random
import logging
import csv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Секреты
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')
GROQ_KEY = os.getenv('GROQ_API_KEY')
FLORI_USER = os.getenv('FLORI_USER')
FLORI_PASS = os.getenv('FLORI_PASS')

async def get_full_stock():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            logger.info("Авторизация во Florisoft...")
            await page.goto("https://flosal.florisoft-cloud.com/login", wait_until="networkidle")
            
            # Находим поля ввода более универсально
            await page.wait_for_selector('input[type="password"]', timeout=20000)
            
            # Исправленный блок ввода данных
            await page.fill('input[type="email"], input[name*="user"], input[name*="login"]', str(FLORI_USER))
            await page.fill('input[type="password"]', str(FLORI_PASS))
            
            await page.click('button[type="submit"], .btn-primary, input[type="submit"]')
            await page.wait_for_load_state("networkidle")
            
            # Переход к прайсу
            logger.info("Перехожу к прайсу...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148", wait_until="networkidle")
            await page.wait_for_selector("table", timeout=30000)

            logger.info("Сканирование полного прайса...")
            for _ in range(15): 
                await page.mouse.wheel(0, 3000)
                await asyncio.sleep(1.5)

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
            await browser.close()
            return []

def save_to_csv(items):
    filename = "florisoft_price.csv"
    if not items: return None
    keys = items[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        dict_writer = csv.DictWriter(f, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(items)
    return filename

def generate_pitch(item):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = f"Краткий оффер: {item['name']}, {item['size']}, цена {item['price']}. Используй HTML <b>."
    try:
        res = requests.post(url, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.4}, headers=headers, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🌿 <b>{item['name']}</b> — {item['price']}€"

async def main():
    items = await get_full_stock()
    if not items:
        logger.error("Товары не найдены или ошибка входа.")
        return

    # Сохраняем файл
    csv_file = save_to_csv(items)

    # Выбираем 5 товаров
    hot_deals = random.sample(items, min(len(items), 5))
    
    logger.info(f"Найдено {len(items)} товаров. Отправляю 5 предложений...")

    for item in hot_deals:
        pitch = generate_pitch(item)
        caption = f"🔥 <b>ГОРЯЧЕЕ ПРЕДЛОЖЕНИЕ</b>\n\n{pitch}\n\n📍 В наличии: {item['stock']} шт."
        
        if item['photo'] and 'http' in item['photo']:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                          json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": caption, "parse_mode": "HTML"})
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"})

    # Отправляем файл
    if csv_file:
        with open(csv_file, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": f"📄 Полный прайс Florisoft\nВсего позиций: {len(items)}"},
                          files={"document": f})

if __name__ == "__main__":
    asyncio.run(main())
