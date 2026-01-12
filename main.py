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
            logger.info("Вход...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            await asyncio.sleep(10)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(5)

            logger.info("Раздел Planten...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            await page.wait_for_selector('tr', timeout=30000)
            await asyncio.sleep(10)

            # ЧАСТЬ 1: Сбор товаров для постов
            products = await page.evaluate('''() => {
                const results = [];
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€'));
                rows.slice(0, 30).forEach(row => {
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

            # ЧАСТЬ 2: Клик по принтеру (сначала пробуем найти его координаты)
            logger.info("Скачиваю прайс...")
            try:
                async with page.expect_download(timeout=60000) as download_info:
                    # Ищем иконку принтера на зеленой полосе
                    printer = page.locator('.fa-print').first
                    await printer.scroll_into_view_if_needed()
                    # Кликаем принудительно через JS для надежности
                    await printer.evaluate("el => el.click()")
                
                download = await download_info.value
                price_path = f"./{download.suggested_filename}"
                await download.save_as(price_path)
            except Exception as e:
                logger.warning(f"Принтер не поддался: {e}. Попробуем постить только товары.")
                price_path = None

            await browser.close()
            return products, price_path

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await browser.close()
            return [], None

def generate_pitch(item):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = f"Напиши очень коротко и по-деловому: {item['name']}, горшок {item['size']}, цена {item['price']}. Используй HTML <b>."
    try:
        res = requests.post(url, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}, headers=headers, timeout=15)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🌿 <b>{item['name']}</b> ({item['size']}) — {item['price']}"

async def main():
    items, price_file = await work_with_florisoft()
    
    # Сначала шлем посты
    if items:
        hot_deals = random.sample(items, min(len(items), 5))
        for item in hot_deals:
            pitch = generate_pitch(item)
            caption = f"🔥 <b>ПОСТУПЛЕНИЕ</b>\n\n{pitch}\n\n📦 Склад: {item['stock']} шт."
            if item['photo'] and 'http' in item['photo']:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": caption, "parse_mode": "HTML"})
            else:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"})
            await asyncio.sleep(3)

    # В конце шлем файл
    if price_file:
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📄 Полный прайс (Planten)"}, files={"document": f})
        os.remove(price_file)

if __name__ == "__main__":
    asyncio.run(main())
