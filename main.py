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

async def get_real_stock():
    async with async_playwright() as p:
        # Запускаем браузер
        browser = await p.chromium.launch(headless=True)
        # Создаем контекст и подставляем твои Cookies
        context = await browser.new_context()
        
        # Превращаем строку куки из GitHub в формат для браузера
        cookie_list = []
        for c in FLORI_COOKIES.split(';'):
            if '=' in c:
                name, value = c.strip().split('=', 1)
                cookie_list.append({"name": name, "value": value, "domain": "flosal.florisoft-cloud.com", "path": "/"})
        
        await context.add_cookies(cookie_list)
        page = await context.new_page()
        
        logger.info("Захожу на склад Florisoft...")
        # Переходим на страницу наличия (твоя ссылка из cURL)
        await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148", wait_until="networkidle")
        
        # Ждем 5 секунд, чтобы Blazor прогрузил таблицу
        await asyncio.sleep(5)
        
        # Пытаемся собрать данные из таблицы (селекторы примерные, зависят от верстки)
        # Мы ищем все строки, где есть данные о товарах
        products = []
        try:
            # Этот скрипт соберет данные прямо из ячеек таблицы браузера
            products = await page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('tr')); // Берем все строки таблицы
                return rows.slice(1, 10).map(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 5) return null;
                    return {
                        name: cells[1]?.innerText.trim(),
                        price: cells[4]?.innerText.trim(),
                        size: cells[2]?.innerText.trim(),
                        stock: cells[3]?.innerText.trim()
                    };
                }).filter(i => i && i.name);
            }''')
        except Exception as e:
            logger.error(f"Ошибка при чтении таблицы: {e}")

        await browser.close()
        
        if products:
            logger.info(f"Найдено товаров: {len(products)}")
            return random.choice(products)
        else:
            # Если не смогли спарсить, вернем заглушку, чтобы бот не падал
            return {"name": "Ficus Lyrata (Offline)", "price": "14.50", "size": "17/60", "stock": "10"}

def generate_pitch(item):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    
    prompt = (
        f"Ты - эксперт по закупкам. Сделай краткое предложение по лоту: {item['name']}. "
        f"Цена: {item['price']}. Параметры: {item['size']}. Остаток: {item['stock']}. "
        "Пиши только по делу: название, ТТХ, цена, ликвидность. Используй HTML: <b>, <i>."
    )
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": prompt}],
        "temperature": 0.2
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🔥 <b>{item['name']}</b> по цене {item['price']}"

async def main():
    item = await get_real_stock()
    pitch = generate_pitch(item)
    
    full_post = (
        f"💹 <b>LIVE STOCK: Florisoft</b>\n"
        f"────────────────────\n\n"
        f"{pitch}\n\n"
        f"────────────────────\n"
        f"🚛 <i>Актуально на текущий момент</i>\n"
        f"#Опт #Закупки #Flowersale"
    )

    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                  json={"chat_id": CHANNEL_ID, "text": full_post, "parse_mode": "HTML"})

if __name__ == "__main__":
    asyncio.run(main())
