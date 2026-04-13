import os
import logging
import aiohttp
import asyncio
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from rembg import remove as rembg_remove

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

ADDRESSES = {
    "ТП": "пр. Победы, 4 / 1-я Техническая, 16И",
    "ЛИ": "пр. Ленина, 28 / Ильича, 74б",
    "БХ": "Б. Хмельницкого, 79б",
}

TITLES = {
    "ОБНОВЛЕНИЕ": "ПОЛНОЕ ОБНОВЛЕНИЕ",
    "ДОВОЗ": "НОВЫЙ ДОВОЗ",
    "СКИДКИ": "СКИДКИ 50-90%",
}

pending = {}
user_state = {}


def remove_background(image_bytes: bytes) -> bytes:
    """Remove background using rembg (local, free)"""
    try:
        result = rembg_remove(image_bytes)
        return result
    except Exception as e:
        logger.error(f"rembg error: {e}")
        return image_bytes


def create_card(product_image: bytes, title: str, subtitle: str,
                item_name: str, brand: str, size: str, price: str,
                address: str) -> bytes:
    """Create Instagram card in Tsenopad Plus style"""
    W, H = 1080, 1350

    # Beige background
    card = Image.new("RGB", (W, H), color=(232, 228, 218))
    draw = ImageDraw.Draw(card)

    # Red top bar
    draw.rectangle([0, 0, W, 75], fill=(204, 28, 28))

    # Try fonts
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 82)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 33)
        font_item = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
        font_addr = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except:
        font_big = ImageFont.load_default()
        font_sub = font_big
        font_item = font_big
        font_addr = font_big

    # Subtitle in red bar
    draw.text((W // 2, 37), subtitle, font=font_sub, fill="white", anchor="mm")

    # Main title
    draw.text((W // 2, 170), title, font=font_big, fill=(15, 15, 15), anchor="mm")

    # Divider line
    draw.rectangle([60, 215, W - 60, 218], fill=(180, 175, 165))

    # Product image
    try:
        img = Image.open(BytesIO(product_image)).convert("RGBA")
        img.thumbnail((920, 860), Image.LANCZOS)
        paste_x = (W - img.width) // 2
        paste_y = 240 + (860 - img.height) // 2
        card.paste(img, (paste_x, paste_y), img)
    except Exception as e:
        logger.error(f"Image paste error: {e}")

    # Item info block
    info_y = 1130
    line1 = f"{item_name}"
    if brand and brand != "-":
        line1 += f"  {brand}"
    draw.text((80, info_y), line1, font=font_item, fill=(15, 15, 15))
    draw.text((80, info_y + 52), f"Размер: {size}   •   Цена: {price} р", font=font_item, fill=(15, 15, 15))

    # Bottom black bar
    draw.rectangle([0, H - 72, W, H], fill=(15, 15, 15))
    draw.text((80, H - 36), address, font=font_addr, fill="white", anchor="lm")
    draw.text((W - 80, H - 36), "10:00 — 20:00", font=font_addr, fill=(200, 28, 28), anchor="rm")

    output = BytesIO()
    card.convert("RGB").save(output, format="JPEG", quality=93)
    return output.getvalue()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👗 Привет! Бот магазина Ценопад Плюс.\n\n"
        "Как пользоваться:\n"
        "1. Отправь фото товара\n"
        "2. Напиши: <магазин> <название> <бренд> <размер> <цена>\n\n"
        "Коды магазинов:\n"
        "ТП — пр. Победы / Техническая\n"
        "ЛИ — пр. Ленина / Ильича\n"
        "БХ — Б. Хмельницкого\n\n"
        "Пример:\nФото куртки + текст: ТП Куртка Zara 44 8"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_bytes = bytes(await file.download_as_bytearray())

    user_state[update.effective_user.id] = {
        "photo": photo_bytes,
        "msg_id": update.message.message_id
    }
    await update.message.reply_text(
        "📸 Фото получено! Теперь напиши:\n"
        "<магазин> <название> <бренд> <размер> <цена>\n\n"
        "Пример: ТП Куртка Zara 44 8"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()

    if uid not in user_state:
        await update.message.reply_text("Сначала отправь фото товара.")
        return

    state = user_state.pop(uid)
    photo_bytes = state["photo"]

    parts = text.split()
    if len(parts) < 4:
        await update.message.reply_text(
            "❌ Формат: <магазин> <название> <бренд> <размер> <цена>\n"
            "Пример: ТП Куртка Zara 44 8"
        )
        user_state[uid] = state
        return

    shop_code = parts[0].upper()
    item_name = parts[1]
    brand = parts[2] if len(parts) > 2 else "-"
    size = parts[3] if len(parts) > 3 else "-"
    price = parts[4] if len(parts) > 4 else "-"
    address = ADDRESSES.get(shop_code, "Гомель")

    await update.message.reply_text("⏳ Вырезаю фон и создаю карточку...")

    # Remove background in thread (CPU intensive)
    loop = asyncio.get_event_loop()
    clean_image = await loop.run_in_executor(None, remove_background, photo_bytes)

    # Create card
    card_bytes = create_card(
        product_image=clean_image,
        title="ПОЛНОЕ ОБНОВЛЕНИЕ",
        subtitle="ЦЕНОПАД ПЛЮС • ОДЕЖДА НА ВЕС",
        item_name=item_name,
        brand=brand,
        size=size,
        price=price,
        address=address
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Одобрить", callback_data=f"ok_{update.message.message_id}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"no_{update.message.message_id}")
    ]])

    await update.message.reply_photo(
        photo=BytesIO(card_bytes),
        caption=f"📋 {item_name} {brand} | Рр {size} | {price}р\n📍 {address}",
        reply_markup=keyboard
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("ok_"):
        await query.edit_message_caption("✅ Одобрено! Готово к публикации в Instagram.")
    elif query.data.startswith("no_"):
        await query.edit_message_caption("❌ Отклонено.")


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
