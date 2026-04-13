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

BRAND_STYLE = """Создай обложку для Instagram магазина секонд-хэнд "Ценопад Плюс" (одежда на вес).
Стиль бренда:
- Цветовая палитра: голубой, бордовый, бежевый, белый
- Фон: светлый, минималистичный, архитектурные элементы
- Типографика: жирный белый sans-serif текст, крупный заголовок на русском языке
- Логотип "ЦЕНОПАД ПЛЮС" в углу
- Формат: вертикальный для Instagram Stories
- Стиль: модный лукбук, editorial, чистый и современный
- Женская мода, одежда, аксессуары
Запрос: """


async def generate_image(prompt: str) -> bytes | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-preview-image-generation:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": BRAND_STYLE + prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "responseMimeType": "text/plain"
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                    if "inlineData" in part:
                        return base64.b64decode(part["inlineData"]["data"])
                logger.error("No image in response")
                return None
            else:
                error = await resp.text()
                logger.error(f"Gemini error {resp.status}: {error}")
                return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот магазина Ценопад Плюс.\n\n"
        "Напиши запрос - я создам обложку для Instagram!\n\n"
        "Примеры:\n"
        "- полное обновление\n"
        "- скидки 50-90%\n"
        "- новая коллекция пальто\n"
        "- весенняя распродажа"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    logger.info(f"Получен запрос: {user_text}")
    await update.message.reply_text("Генерирую обложку, подожди 20-30 секунд...")
    image_bytes = await generate_image(user_text)
    if image_bytes:
        await update.message.reply_photo(
            photo=BytesIO(image_bytes),
            caption=f"Готово! Запрос: {user_text}"
        )
    else:
        await update.message.reply_text("Не удалось создать картинку. Попробуй другой запрос.")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
