import asyncio
import logging
import io

from aiogram.types import BufferedInputFile
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.filters import Command

from PIL import Image, ImageDraw, ImageFont

import CONFIG


# ==================================================
# ЛОГИРОВАНИЕ
# ==================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ==================================================
# ГЕНЕРАЦИЯ ЦЕННИКА (БЕЗ ПАДЕНИЙ)
# ==================================================
# ГЕНЕРАЦИЯ PNG
# ==================================================
def generate_compressed_png(name: str, price: str, weight: str) -> bytes:
    try:
        WIDTH, HEIGHT = 1100, 320
        BG = "#0f0f0f"

        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)

        PADDING = 32
        PRICE_ZONE_WIDTH = 280
        TEXT_ZONE_WIDTH = WIDTH - PRICE_ZONE_WIDTH - PADDING * 2

        # ---------- Шрифты ----------
        def load_font(size, bold=False):
            try:
                return ImageFont.truetype(
                    "arialbd.ttf" if bold else "arial.ttf", size
                )
            except:
                return ImageFont.load_default()

        def safe_len(text, font):
            try:
                return draw.textlength(text, font=font)
            except:
                return len(text) * font.size * 0.6

        # ---------- Название (короткое = очень крупно) ----------
        title = name.upper()

        if len(title) <= 6:
            MAX_FONT = 72   # 👈 КОРОТКИЕ НАЗВАНИЯ
        else:
            MAX_FONT = 56

        MIN_FONT = 30
        LINE_SPACING = 8

        def split_two_lines(text, font):
            words = text.split()
            line1, line2 = "", ""

            for word in words:
                test = f"{line1} {word}".strip()
                if safe_len(test, font) <= TEXT_ZONE_WIDTH:
                    line1 = test
                else:
                    line2 += f" {word}"

            return line1.strip(), line2.strip()

        font_size = MAX_FONT

        while font_size >= MIN_FONT:
            font_title = load_font(font_size, True)
            line1, line2 = split_two_lines(title, font_title)

            lines = 2 if line2 else 1
            total_h = lines * font_size + (LINE_SPACING if line2 else 0)

            if total_h <= HEIGHT - 90:
                break

            font_size -= 2

        font_title = load_font(font_size, True)
        line1, line2 = split_two_lines(title, font_title)

        total_text_height = font_size * (2 if line2 else 1) + (LINE_SPACING if line2 else 0)
        text_y = (HEIGHT - total_text_height) // 2

        draw.text((PADDING, text_y), line1, fill="white", font=font_title)
        if line2:
            draw.text(
                (PADDING, text_y + font_size + LINE_SPACING),
                line2,
                fill="white",
                font=font_title
            )

        # ---------- Вес (СДЕЛАЛИ КРУПНЕЕ) ----------
        draw.text(
            (PADDING, HEIGHT - 42),
            f"{weight} г",
            fill="#d9d9d9",
            font=load_font(34)  # 👈 было 28
        )

        # ---------- Разделитель ----------
        divider_x = WIDTH - PRICE_ZONE_WIDTH
        draw.line(
            [(divider_x, 20), (divider_x, HEIGHT - 20)],
            fill="#4a4a4a",
            width=2
        )

        # ---------- Цена ----------
        price_text = str(price)
        font_price = load_font(120, True)

        bbox = draw.textbbox((0, 0), price_text, font=font_price)
        pw = bbox[2] - bbox[0]
        ph = bbox[3] - bbox[1]

        price_x = divider_x + (PRICE_ZONE_WIDTH - pw) // 2
        price_y = (HEIGHT - ph) // 2 - 10

        draw.text((price_x, price_y), price_text, fill="white", font=font_price)
        draw.text(
            (price_x + pw + 6, price_y + ph - 40),
            "₽",
            fill="white",
            font=load_font(42, True)
        )

        # ---------- Водяной знак (темнее и у цены) ----------
        draw.text(
            (divider_x + 16, 18),
            "Хлебный цех",
            fill=(255, 255, 255, 90),  # 👈 темнее
            font=load_font(22)
        )

        # ---------- Сохранение ----------
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception:
        logging.exception("❌ Ошибка генерации ценника")

        img = Image.new("RGB", (500, 200), "#8b0000")
        draw = ImageDraw.Draw(img)
        draw.text((20, 80), "ОШИБКА ЦЕННИКА", fill="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
def generate_compact_png(name: str, price: str, weight: str) -> bytes:
    WIDTH, HEIGHT = 420, 320
    BG = "#0f0f0f"
    PADDING = 24

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # ---------- utils ----------
    def load_font(size, bold=False):
        try:
            return ImageFont.truetype(
                "arialbd.ttf" if bold else "arial.ttf", size
            )
        except:
            return ImageFont.load_default()

    def safe_len(text, font):
        try:
            return draw.textlength(text, font=font)
        except:
            return len(text) * font.size * 0.6

    # ---------- зоны ----------
    TOP_ZONE = 36          # водяной знак
    BOTTOM_ZONE = 110      # цена + вес
    FREE_HEIGHT = HEIGHT - TOP_ZONE - BOTTOM_ZONE

    # ---------- водяной знак ----------
    draw.text(
        (PADDING, 10),
        "Хлебный цех",
        fill=(255, 255, 255, 80),
        font=load_font(18)
    )

    # ---------- НАЗВАНИЕ (автоскейл + центр зоны) ----------
    title = name.upper()

    # короткие названия можно сильнее увеличить
    MAX_FONT = 54 if len(title) <= 10 else 46
    MIN_FONT = 28
    LINE_SPACING = 6

    def split_two_lines(text, font):
        words = text.split()
        line1, line2 = "", ""

        for w in words:
            test = f"{line1} {w}".strip()
            if safe_len(test, font) <= WIDTH - PADDING * 2:
                line1 = test
            else:
                line2 += f" {w}"

        return line1.strip(), line2.strip()

    font_size = MAX_FONT

    while font_size >= MIN_FONT:
        font_title = load_font(font_size, True)
        line1, line2 = split_two_lines(title, font_title)

        lines = 2 if line2 else 1
        total_h = lines * font_size + (LINE_SPACING if line2 else 0)

        if total_h <= FREE_HEIGHT:
            break

        font_size -= 2

    font_title = load_font(font_size, True)
    line1, line2 = split_two_lines(title, font_title)

    total_text_height = font_size * (2 if line2 else 1) + (LINE_SPACING if line2 else 0)
    text_y = TOP_ZONE + (FREE_HEIGHT - total_text_height) // 2

    draw.text((PADDING, text_y), line1, fill="white", font=font_title)
    if line2:
        draw.text(
            (PADDING, text_y + font_size + LINE_SPACING),
            line2,
            fill="white",
            font=font_title
        )

    # ---------- ЦЕНА (жёстко внизу) ----------
    font_price = load_font(92, True)
    bbox = draw.textbbox((0, 0), price, font=font_price)
    ph = bbox[3] - bbox[1]

    price_y = HEIGHT - BOTTOM_ZONE + 20
    draw.text(
        (PADDING, price_y),
        price,
        fill="white",
        font=font_price
    )

    # ---------- ₽ ----------
    draw.text(
        (PADDING + bbox[2] + 6, price_y + ph - 42),
        "₽",
        fill="white",
        font=load_font(36, True)
    )

    # ---------- ВЕС (справа от цены) ----------
    draw.text(
        (WIDTH - 80, price_y + ph - 28),
        weight,
        fill="#cfcfcf",
        font=load_font(32)
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer.getvalue()

# ==================================================
# PNG → PDF
# ==================================================
def png_to_pdf(png_bytes: bytes) -> bytes:
    image = Image.open(io.BytesIO(png_bytes)).convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="PDF")
    buffer.seek(0)

    return buffer.getvalue()


# ==================================================
# КНОПКА PDF
# ==================================================
def pdf_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📄 Создать PDF",
                    callback_data="make_pdf"
                )
            ]
        ]
    )


# ==================================================
# ХРАНЕНИЕ PNG
# ==================================================
user_last_png = {}

# ==================================================
# BOT / DISPATCHER
# ==================================================
bot = Bot(token=CONFIG.BOT_TOKEN)
dp = Dispatcher()


# ==================================================
# ХЭНДЛЕРЫ
# ==================================================
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Отправь сообщение в формате:\n"
        "1️⃣ Название, Цена, Вес  — большой ценник\n"
        "2️⃣ Название Цена Вес    — компактный\n\n"
        "Примеры:\n"
        "Чиабатта пшеничная мини, 89, 230\n"
        "Сэндвич с рыбой 299 170"
    )


@dp.message(F.text)
async def process_label(message: Message):
    text = message.text.strip()
    logging.info(f"📩 Получено сообщение: {text}")

    # ---------- ФОРМАТ С ЗАПЯТЫМИ (БОЛЬШОЙ) ----------
    if "," in text:
        parts = [p.strip() for p in text.split(",")]
        if len(parts) < 3:
            await message.answer("Формат: Название, Цена, Вес")
            return

        name = parts[0]
        price = "".join(filter(str.isdigit, parts[1]))
        weight = "".join(filter(str.isdigit, parts[2]))

        png_bytes = generate_compressed_png(name, price, weight)

    # ---------- ФОРМАТ С ПРОБЕЛАМИ (КОМПАКТНЫЙ) ----------
    else:
        parts = text.split()
        if len(parts) < 3:
            await message.answer("Формат: Название Цена Вес")
            return

        price = "".join(filter(str.isdigit, parts[-2]))
        weight = "".join(filter(str.isdigit, parts[-1]))
        name = " ".join(parts[:-2])

        png_bytes = generate_compact_png(name, price, weight)

    logging.info(f"🖼 PNG размер: {len(png_bytes)} байт")

    if not png_bytes or len(png_bytes) < 1000:
        await message.answer("❌ Ошибка генерации изображения")
        return

    photo = BufferedInputFile(png_bytes, filename="label.png")
    user_last_png[message.from_user.id] = png_bytes

    await message.answer_photo(
        photo=photo,
        caption="✅ Ценник готов",
        reply_markup=pdf_keyboard()
    )


@dp.callback_query(F.data == "make_pdf")
async def make_pdf(callback):
    logging.info("📄 Нажата кнопка PDF")

    user_id = callback.from_user.id
    if user_id not in user_last_png:
        await callback.message.answer("❌ Нет изображения для PDF")
        await callback.answer()
        return

    png_bytes = user_last_png[user_id]
    pdf_bytes = png_to_pdf(png_bytes)

    await callback.message.answer_document(
        document=BufferedInputFile(pdf_bytes, filename="label.pdf"),
        caption="📄 PDF ценника"
    )

    await callback.answer()

# ==================================================
# АВТОТЕСТ ГЕНЕРАТОРА
# ==================================================
def test_label_generator():
    test = generate_compressed_png(
        "Чиабатта пшеничная мини",
        "89",
        "230"
    )
    assert test and len(test) > 1000
    logging.info("✅ Генератор ценников работает")


# ==================================================
# MAIN
# ==================================================
async def main():
    logging.info("🚀 Бот запускается")

    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"❌ Polling упал: {e}")
            await asyncio.sleep(5)
if __name__ == "__main__":
    asyncio.run(main())