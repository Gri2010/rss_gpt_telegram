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
FLORI_COOKIES = os.getenv('FLORI_COOKIES')

async def get_all_stock():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        
        cookie_list = []
        for c in FLORI_COOKIES.split(';'):
            if '=' in c:
                name, value = c.strip().split('=', 1)
                cookie_list.append({"name": name, "value": value, "domain": "flosal.florisoft-cloud.com", "path": "/"})
        
        await context.add_cookies(cookie_list)
        page = await context.new_page()
        
        try:
            logger.info("Подключаемся к Florisoft...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148", wait_until="networkidle", timeout=60000)
            
            # Листаем страницу вниз, чтобы подгрузились картинки (Lazy Load)
            for _ in range(5):
                await page.mouse.wheel(0, 800)
                await asyncio.sleep(1)
            
            await asyncio.sleep(5) 

            # Собираем все товары, у которых есть цена
            products = await page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€'));
                return rows.map(row => {
                    const cells = row.querySelectorAll('td');
                    const img = row.querySelector('img');
                    if (cells.length < 5) return null;
                    return {
                        name: cells[1]?.innerText.trim(),
                        size: cells[2]?.innerText.trim(),
                        stock: cells[3]?.innerText.trim(),
                        price: cells[4]?.innerText.trim(),
                        photo: img ? img.src : null
                    };
                }).filter(i => i && i.name.length > 2);
            }''')

            await browser.close()
            return products
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            await browser.close()
            return []

def generate_pitch(item):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = (
        f"Ты эксперт по закупкам растений. Напиши краткое предложение: "
        f"{item['name']}, ТТХ: {item['size']}, Цена: {item['price']}, Остаток: {item['stock']}. "
        "Стиль: четко, профессионально, с эмодзи. Используй HTML <b>."
    )
    try:
        res = requests.post(url, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}, headers=headers)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🌿 <b>{item['name']}</b>\nЦена: {item['price']}"

async def main():
    products = await get_all_stock()
    if not products:
        logger.error("Товары не найдены.")
        return

    # Берем, например, 5 случайных товаров для этой сессии
    sample_size = min(len(products), 5)
    selected_items = random.sample(products, sample_size)
    
    logger.info(f"Выбрано {sample_size} товаров. Начинаю рассылку раз в 3 минуты...")

    for index, item in enumerate(selected_items):
        pitch = generate_pitch(item)
        caption = f"💹 <b>HOT OFFER: FLOWERSALE</b>\n────────────────────\n\n{pitch}\n\n────────────────────\n📩 @твой_контакт для заказа"

        if item['photo'] and 'http' in item['photo']:
            send_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            payload = {"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": caption, "parse_mode": "HTML"}
        else:
            send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"}

        requests.post(send_url, json=payload)
        logger.info(f"Пост {index+1} отправлен.")

        # Если это не последний товар, ждем 3 минуты (180 секунд)
        if index < sample_size - 1:
            await asyncio.sleep(180)

if __name__ == "__main__":
    asyncio.run(main())
