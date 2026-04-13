import os
import logging
import aiohttp
from io import BytesIO
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

BRAND_STYLE = "Instagram Stories cover for second-hand clothing store, fashion editorial style, minimalist architecture background, light blue and burgundy colors, bold white Russian text, vertical 9:16 format, luxury fashion lookbook aesthetic, "


async def generate_image(prompt: str) -> bytes | None:
    full_prompt = BRAND_STYLE + prompt
    encoded = full_prompt.replace(" ", "%20")
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status == 200:
                return await resp.read()
            else:
                logger.error(f"Pollinations error {resp.status}")
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
