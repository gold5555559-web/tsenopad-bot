import os
import logging
import asyncio
import aiohttp
import base64
import json
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

BRAND_STYLE = """
Создай обложку для Instagram магазина секонд-хэнд "Ценопад Плюс" (одежда на вес).
Стиль бренда:
- Цветовая палитра: голубой (#A8C5D8), бордовый (#6B1B2A), бежевый (#E8DDD0), белый, тёмно-красный низ
- Фон: светлый, минималистичный, архитектурные элементы (бетон, вода, небо)
- Типографика: жирный белый sans-serif текст, крупный заголовок
- Логотип "ЦЕНОПАД ПЛЮС / ОДЕЖДА НА ВЕС" в правом нижнем углу (маленький, полупрозрачный)
- Формат: вертикальный 9:16, для Instagram Stories
- Стиль фотографии: модный лукбук, editorial, чистый и современный
- Женская мода, одежда, аксессуары
- Текст на русском языке на обложке
Запрос пользователя:
"""

async def generate_image_gemini(prompt: str) -> bytes | None:
    """Generate image using Google Gemini Imagen API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-001:predict?key={GEMINI_API_KEY}"
    
    full_prompt = BRAND_STYLE + prompt
    
    payload = {
        "instances": [
            {"prompt": full_prompt}
        ],
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
                image_b64 = data["predictions"][0]["bytesBase64Encoded"]
                return base64.b64decode(image_b64)
            else:
                error = await resp.text()
                logger.error(f"Gemini API error: {resp.status} — {error}")
                return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👗 Привет! Я бот магазина *Ценопад Плюс*.\n\n"
        "Напиши мне простой запрос, и я создам обложку для Instagram!\n\n"
        "Примеры:\n"
        "• _полное обновление_\n"
        "• _скидки 50-90%_\n"
        "• _новая коллекция пальто_\n"
        "• _весенняя распродажа_",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()
    
    await update.message.reply_text("⏳ Генерирую обложку, подожди 15–30 секунд...")
    
    image_bytes = await generate_image_gemini(user_text)
    
    if image_bytes:
        await update.message.reply_photo(
            photo=BytesIO(image_bytes),
            caption=f"✅ Обложка готова!\n📝 Запрос: _{user_text}_",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось сгенерировать картинку. Попробуй другой запрос или повтори позже."
        )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
