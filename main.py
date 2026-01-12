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
FLORI_USER = os.getenv('FLORI_USER')
FLORI_PASS = os.getenv('FLORI_PASS')

async def work_with_florisoft():
    async with async_playwright() as p:
        # Увеличим время ожидания браузера
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            logger.info("Авторизация...")
            await page.goto("https://www.flowersale.nl/", wait_until="networkidle")
            await page.get_by_text("Login Webshop").first.click()
            await page.wait_for_selector('input[placeholder*="Gebruiker"]')
            await page.fill('input[placeholder*="Gebruiker"]', str(FLORI_USER))
            await page.fill('input[placeholder*="Wachtwoord"]', str(FLORI_PASS))
            await page.click('button:has-text("INLOGGEN")')
            
            await asyncio.sleep(12)
            await page.keyboard.press("Enter") 
            await asyncio.sleep(5)

            logger.info("Загрузка прайса...")
            await page.goto("https://flosal.florisoft-cloud.com/Voorraad/PLANT_/PLANT/TP148")
            
            # Ждем появления хотя бы одной строки с ценой (символом €)
            try:
                await page.wait_for_selector('text=€', timeout=30000)
            except:
                logger.warning("Символ € не найден вовремя, пробуем скроллить...")

            # Скроллим немного вниз и вверх, чтобы Blazor "проснулся"
            await page.mouse.wheel(0, 500)
            await asyncio.sleep(3)
            await page.mouse.wheel(0, -500)
            await asyncio.sleep(5)

            # --- ГИБКИЙ СБОР ДАННЫХ ---
            products = await page.evaluate('''() => {
                const results = [];
                // Ищем все строки таблицы
                const rows = Array.from(document.querySelectorAll('tr'));
                
                for (let row of rows) {
                    const text = row.innerText;
                    // Если в строке есть цена (цифра с запятой и €)
                    if (text.includes('€')) {
                        const cells = Array.from(row.querySelectorAll('td')).map(c => c.innerText.trim());
                        const img = row.querySelector('img');
                        
                        if (cells.length >= 4) {
                            results.push({
                                // Пытаемся угадать столбцы: обычно Название(1), Размер(2), Сток(3), Цена(4)
                                name: cells[1] || "Без названия",
                                size: cells[2] || "",
                                stock: cells[3] || "0",
                                price: cells[4] || "0",
                                photo: img ? img.src : null
                            });
                        }
                    }
                }
                return results;
            }''')
            
            logger.info(f"Найдено позиций: {len(products)}")

            # --- ПОПЫТКА СКАЧИВАНИЯ ---
            price_path = None
            try:
                await page.locator('.fa-print').first.click()
                await asyncio.sleep(5)
                async with page.expect_download(timeout=30000) as download_info:
                    await page.keyboard.press("Enter")
                download = await download_info.value
                price_path = f"./price_list.pdf"
                await download.save_as(price_path)
            except:
                pass

            await browser.close()
            return products, price_path

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await page.screenshot(path="last_debug.png")
            # Если совсем беда - шлем скриншот в ТГ
            with open("last_debug.png", "rb") as f:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                              data={"chat_id": CHANNEL_ID, "caption": "Ошибка парсинга таблицы"}, files={"photo": f})
            await browser.close()
            return [], None

async def main():
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                  json={"chat_id": CHANNEL_ID, "text": "🚀 Бот в работе. Проверяю остатки Planten..."})

    items, price_file = await work_with_florisoft()
    
    if not items:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": CHANNEL_ID, "text": "⚠️ Товары не считались. Попробую в следующем цикле."})
        return

    # Выбираем 5 случайных позиций
    selected = random.sample(items, min(len(items), 5))
    for item in selected:
        msg = (f"🌿 <b>{item['name']}</b>\n\n"
               f"📏 Параметры: {item['size']}\n"
               f"💰 Цена: {item['price']}\n"
               f"📦 Доступно: {item['stock']}")
        
        if item['photo'] and 'http' in item['photo']:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                          json={"chat_id": CHANNEL_ID, "photo": item['photo'], "caption": msg, "parse_mode": "HTML"})
        else:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          json={"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "HTML"})
        await asyncio.sleep(2)

    if price_file:
        with open(price_file, "rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendDocument", 
                          data={"chat_id": CHANNEL_ID, "caption": "📄 Полный прайс"}, files={"document": f})

if __name__ == "__main__":
    asyncio.run(main())
