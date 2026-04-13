import asyncio
import logging
import io
from pathlib import Path

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
def draw_wheat_logo(draw, canvas_width: int, *, size: int, top_margin: int, right_margin: int) -> None:
    # Небольшой программный тонкий колос в правом верхнем углу без внешних файлов.
    base_x = canvas_width - right_margin - size
    base_y = top_margin

    stem_width = max(2, size // 14)
    branch_width = max(1, stem_width - 1)
    grain_radius = max(2, size // 12)

    def point(rel_x: float, rel_y: float):
        return (
            int(base_x + size * rel_x),
            int(base_y + size * rel_y)
        )

    stem_start = point(0.20, 0.96)
    stem_mid = point(0.36, 0.56)
    stem_end = point(0.58, 0.12)
    draw.line([stem_start, stem_mid, stem_end], fill="white", width=stem_width)

    for rel_x, rel_y in [
        (0.30, 0.78),
        (0.38, 0.62),
        (0.46, 0.46),
        (0.54, 0.30),
    ]:
        center = point(rel_x, rel_y)
        left_tip = point(rel_x - 0.16, rel_y - 0.08)
        right_tip = point(rel_x + 0.12, rel_y - 0.10)

        draw.line([center, left_tip], fill="white", width=branch_width)
        draw.line([center, right_tip], fill="white", width=branch_width)

        draw.ellipse(
            [
                left_tip[0] - grain_radius,
                left_tip[1] - grain_radius,
                left_tip[0] + grain_radius,
                left_tip[1] + grain_radius
            ],
            fill="white"
        )
        draw.ellipse(
            [
                right_tip[0] - grain_radius,
                right_tip[1] - grain_radius,
                right_tip[0] + grain_radius,
                right_tip[1] + grain_radius
            ],
            fill="white"
        )

    top_tip = point(0.66, 0.04)
    draw.line([stem_end, top_tip], fill="white", width=branch_width)
    draw.ellipse(
        [
            top_tip[0] - grain_radius,
            top_tip[1] - grain_radius,
            top_tip[0] + grain_radius,
            top_tip[1] + grain_radius
        ],
        fill="white"
    )


def add_wheat_logo(img, draw, canvas_width: int, *, size: int, top_margin: int, right_margin: int) -> None:
    base_dir = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
    logo_path = base_dir / "assets" / "wheat_white.png"

    if logo_path.exists():
        try:
            with Image.open(logo_path) as logo_source:
                logo = logo_source.convert("RGBA")

            logo.thumbnail((size, size), Image.LANCZOS)
            logo_x = canvas_width - right_margin - logo.width
            img.paste(logo, (logo_x, top_margin), logo)
            return
        except Exception:
            logging.exception("❌ Ошибка загрузки логотипа пшеницы")

    draw_wheat_logo(
        draw,
        canvas_width,
        size=size,
        top_margin=top_margin,
        right_margin=right_margin
    )


def generate_compressed_png(name: str, price: str, weight: str) -> bytes:
    try:
        WIDTH, HEIGHT = 1100, 320
        BG = "#0f0f0f"

        img = Image.new("RGB", (WIDTH, HEIGHT), BG)
        draw = ImageDraw.Draw(img)

        PADDING = 34
        TOP_ZONE = 42
        BOTTOM_ZONE = 68
        PRICE_ZONE_WIDTH = 286
        CONTENT_RIGHT_GAP = 24
        divider_x = WIDTH - PRICE_ZONE_WIDTH
        TEXT_ZONE_WIDTH = divider_x - PADDING * 2 - CONTENT_RIGHT_GAP
        FREE_HEIGHT = HEIGHT - TOP_ZONE - BOTTOM_ZONE

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

        if len(title) <= 10:
            MAX_FONT = 78
        else:
            MAX_FONT = 68

        MIN_FONT = 34
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

            if total_h <= FREE_HEIGHT:
                break

            font_size -= 2

        font_title = load_font(font_size, True)
        line1, line2 = split_two_lines(title, font_title)

        total_text_height = font_size * (2 if line2 else 1) + (LINE_SPACING if line2 else 0)
        text_y = TOP_ZONE + (FREE_HEIGHT - total_text_height) // 2

        # ---------- Правая ценовая зона ----------
        draw.rectangle(
            [(divider_x, 0), (WIDTH, HEIGHT)],
            fill="#131313"
        )
        draw.line(
            [(divider_x, 18), (divider_x, HEIGHT - 18)],
            fill="#3b3b3b",
            width=2
        )

        # ---------- Верхняя подпись ----------
        draw.text(
            (PADDING, 12),
            "Хлебный цех",
            fill=(255, 255, 255, 80),
            font=load_font(20)
        )

        draw.text((PADDING, text_y), line1, fill="white", font=font_title)
        if line2:
            draw.text(
                (PADDING, text_y + font_size + LINE_SPACING),
                line2,
                fill="white",
                font=font_title
            )

        # ---------- Вес ----------
        draw.text(
            (PADDING, HEIGHT - 50),
            f"{weight} г",
            fill="#cfcfcf",
            font=load_font(32)
        )

        # ---------- Цена ----------
        price_text = str(price)
        price_font_size = 132
        price_column_inner_width = PRICE_ZONE_WIDTH - 56

        while price_font_size >= 84:
            font_price = load_font(price_font_size, True)
            bbox = draw.textbbox((0, 0), price_text, font=font_price)
            pw = bbox[2] - bbox[0]
            ph = bbox[3] - bbox[1]

            if pw <= price_column_inner_width:
                break

            price_font_size -= 4

        price_x = divider_x + (PRICE_ZONE_WIDTH - pw) // 2
        price_y = (HEIGHT - ph) // 2 - 8

        draw.text((price_x, price_y), price_text, fill="white", font=font_price)
        draw.text(
            (price_x + pw + 6, price_y + ph - 40),
            "₽",
            fill="white",
            font=load_font(42, True)
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
