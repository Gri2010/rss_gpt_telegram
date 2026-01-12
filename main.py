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
            # 1. Логин
            logger.info("Вход в систему...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            await asyncio.sleep(10)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(5)

            # 2. Переход в Planten
            logger.info("Переход в Planten...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            await asyncio.sleep(12)

            # --- ЧАСТЬ 1: Собираем данные для 5 постов ---
            logger.info("Парсим товары для постов...")
            products = await page.evaluate('''() => {
                const results = [];
                const rows = Array.from(document.querySelectorAll('tr')).filter(r => r.innerText.includes('€'));
                rows.slice(0, 50).forEach(row => { // Берем первые 50 для выбора
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

            # --- ЧАСТЬ 2: Скачиваем полный прайс через принтер ---
            logger.info("Нажимаю на принтер на зеленой полосе...")
            async with page.expect_download(timeout=60000) as download_info:
                # Целимся в иконку принтера на зеленой панели
                await page.locator('.fa-print').first.click()
            
            download = await download_info.value
            price_path = f"./{download.suggested_filename}"
            await download.save_as(price_path)
            
            await browser.close()
            return products, price_path

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await page.screenshot(path="error.png")
            with open("error.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": f"Ошибка: {e}"}, files={"photo": f})
            await browser.close()
            return [], None

def generate_pitch(item):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    prompt = f"Напиши 1 короткое продающее предложение для растения: {item['name']}, размер {item['size']}, цена {item['price']}. Используй HTML <b>."
    try:
        res = requests.post(url, json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}]}, headers=headers, timeout=20)
        return res.json()['choices'][0]['message']['content']
    except:
        return f"🌿 <b>{item['name']}</b> ({item['size']}) — {item['price']}€"

async def main():
    items, price_file = await work_with_florisoft()
    
    # 1. Отправляем 5 постов
    if items:
        hot_deals = random.sample(items, min(len(items), 5))
        for item in hot_deals:
            pitch = generate_pitch(item)
            caption = f"🔥 <b>ПРЕДЛОЖЕНИЕ ДНЯ</b>\n\n{pitch}\n\n📦 В наличии: {item['stock']}"
            if item['photo'] and 'http' in item['photo']:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": caption, "parse_mode": "HTML"})
            else:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"})
            await asyncio.sleep(2)

    # 2. Отправляем файл
    if price_file:
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📄 Полный прайс скачан через систему."}, files={"document": f})
        os.remove(price_file)

if __name__ == "__main__":
    asyncio.run(main())
