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
            # 1. Заходим на главный сайт
            logger.info("Захожу на flowersale.nl...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle", timeout=60000)
            
            # 2. Ищем и кликаем кнопку Login Webshop
            logger.info("Ищу кнопку Login Webshop...")
            # Пытаемся найти кнопку по тексту
            login_button = page.get_by_text("Login Webshop", exact=False)
            await login_button.click()
            
            # Ждем прогрузки страницы логина (она может открыться в той же вкладке)
            await asyncio.sleep(5)
            await page.wait_for_selector('input[placeholder="Gebruikersnaam"]', timeout=30000)

            # 3. Авторизация
            logger.info("Ввожу логин и пароль...")
            await page.fill('input[placeholder="Gebruikersnaam"]', str(FLORI_USER))
            await page.fill('input[placeholder="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            
            # Ждем входа в систему
            await asyncio.sleep(10)
            
            # Если выскочило окно выбора компании - жмем Enter
            await page.keyboard.press("Enter")
            await asyncio.sleep(5)

            # 4. Переход в нужный раздел (PLANTS)
            logger.info("Перехожу в раздел растений...")
            # Используем ту прямую ссылку, что была раньше
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148", wait_until="networkidle")
            await asyncio.sleep(10)

            # Прокрутка для подгрузки всего прайса
            for _ in range(12):
                await page.mouse.wheel(0, 3000)
                await asyncio.sleep(1)

            # 5. Парсинг товаров
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
            logger.error(f"Ошибка на этапе: {e}")
            await page.screenshot(path="login_step_error.png")
            with open("login_step_error.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": f"Ошибка на сайте: {e}"}, files={"photo": f})
            await browser.close()
            return []

def save_to_csv(items):
    filename = "flowersale_price.csv"
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
    prompt = f"Краткий оффер для профи: {item['name']}, {item['size']}, цена {item['price']}. Используй HTML <b>. По-русски."
    try:
        res = requests.post(url, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}, headers=headers, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🌿 <b>{item['name']}</b> ({item['size']}) — {item['price']}€"

async def main():
    items = await get_full_stock()
    if not items:
        return

    csv_file = save_to_csv(items)
    
    # Постим 5 случайных позиций
    hot_deals = random.sample(items, min(len(items), 5))
    for item in hot_deals:
        pitch = generate_pitch(item)
        caption = f"🔥 <b>LIVE STOCK: FLOWERSALE</b>\n\n{pitch}\n\n📍 Доступно: {item['stock']} шт."
        if item['photo'] and 'http' in item['photo']:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": caption, "parse_mode": "HTML"})
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"})

    # Прикрепляем файл
    if csv_file:
        with open(csv_file, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": f"📄 Полный актуальный прайс\nВсего товаров: {len(items)}"}, files={"document": f})

if __name__ == "__main__":
    asyncio.run(main())
