import os
import logging
import aiohttp
import base64
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

BRAND_STYLE = """
Создай обложку для Instagram магазина секонд-хэнд "Ценопад Плюс" (одежда на вес).
Стиль бренда:
- Цветовая палитра: голубой (#A8C5D8), бордовый (#6B1B2A), бежевый (#E8DDD0), белый
- Фон: светлый, минималистичный, архитектурные элементы (бетон, вода, небо)
- Типографика: жирный белый sans-serif текст, крупный заголовок
- Логотип "ЦЕНОПАД ПЛЮС / ОДЕЖДА НА ВЕС" в правом нижнем углу (маленький)
- Формат: вертикальный 9:16, для Instagram Stories
- Стиль: модный лукбук, editorial, чистый и современный
- Женская мода, одежда, аксессуары
- Текст на русском языке на обложке
Запрос пользователя: """

async def generate_image(prompt: str) -> bytes | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={GEMINI_API_KEY}"
    payload = {
        "instances": [{"prompt": BRAND_STYLE + prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": "9:16",
            "safetyFilterLevel": "block_some",
            "personGeneration": "allow_adult"
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return base64.b64decode(data["predictions"][0]["bytesBase64Encoded"])
            else:
                error = await resp.text()
                logger.error(f"Gemini error {resp.status}: {error}")
                return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👗 Привет! Я бот магазина *Ценопад Плюс*.\n\n"
        "Напиши запрос — я создам обложку для Instagram!\n\n"
        "Примеры:\n"
        "• полное обновление\n"
        "• скидки 50-90%\n"
        "• новая коллекция пальто\n"
        "• весенняя распродажа",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    await update.message.reply_text("⏳ Генерирую обложку, подожди 20-30 секунд...")
    image_bytes = await generate_image(user_text)
    if image_bytes:
        await update.message.reply_photo(
            photo=BytesIO(image_bytes),
            caption=f"✅ Готово! Запрос: _{user_text}_",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Не удалось создать картинку. Попробуй другой запрос.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
