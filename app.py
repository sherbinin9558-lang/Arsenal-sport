"""Простой локальный MVP для создания карточек Arsenal Sport."""

import io
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont
 from rembg import remove


PRODUCTS_FILE = Path("products.json")
CARD_SIZE = (1080, 1350)
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Возвращает системный шрифт для изображения."""
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def read_products() -> list[dict]:
    if not PRODUCTS_FILE.exists():
        return []
    try:
        return json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_product(product: dict) -> None:
    products = read_products()
    products.append(product)
    PRODUCTS_FILE.write_text(
        json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fit_photo(photo: Image.Image, remove_background: bool) -> Image.Image:
    photo = photo.convert("RGBA")
    if remove_background:
        photo = remove(photo).convert("RGBA")

    canvas = Image.new("RGBA", (1080, 700), "#e4e5e0")
    photo.thumbnail((980, 620), Image.Resampling.LANCZOS)
    left = (canvas.width - photo.width) // 2
    top = (canvas.height - photo.height) // 2
    canvas.alpha_composite(photo, (left, top))
    return canvas


def split_lines(draw: ImageDraw.ImageDraw, text: str, text_font, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    text_font,
    fill: str,
    max_width: int,
    max_lines: int,
    spacing: int,
) -> int:
    lines = split_lines(draw, text, text_font, max_width)[:max_lines]
    for line in lines:
        draw.text((x, y), line, font=text_font, fill=fill)
        y += text_font.size + spacing
    return y


def create_card(product: dict, photo: Image.Image, remove_background: bool) -> Image.Image:
    card = Image.new("RGBA", CARD_SIZE, "#1b1d1d")
    card.alpha_composite(fit_photo(photo, remove_background), (0, 0))
    draw = ImageDraw.Draw(card)

    # Логотип и служебная строка.
    draw.ellipse((42, 30, 76, 64), fill="#151716")
    draw.text((51, 31), "A", font=font(24, True), fill="#d9ff36")
    draw.text((90, 36), "ARSENAL", font=font(22, True), fill="white")
    draw.text((209, 36), "SPORT", font=font(22, True), fill="#fb604d")
    draw.text((895, 40), "NEW / 01", font=font(15, True), fill="#333633")

    draw.text((52, 750), product["brand"].upper(), font=font(24, True), fill="#d9ff36")
    name_bottom = draw_text_block(
        draw, product["name"].upper(), 52, 792, font(54, True), "white", 950, 2, 5
    )
    description = product.get("description", "")
    if description:
        draw_text_block(draw, description, 52, name_bottom + 22, font(20), "#c3c6c3", 900, 2, 8)

    meta = " · ".join(
        item
        for item in (
            f"Размеры: {product['sizes']}" if product.get("sizes") else "",
            f"Цвет: {product['color']}" if product.get("color") else "",
            f"Арт.: {product['sku']}" if product.get("sku") else "",
        )
        if item
    )
    draw.text((52, 1252), meta, font=font(18), fill="#aeb3af")

    features = [item.strip() for item in product.get("features", "").split(",") if item.strip()]
    feature_y = 1130
    for item in features[:3]:
        draw.text((700, feature_y), f"• {item}", font=font(17), fill="#d9dcda")
        feature_y += 28
    return card.convert("RGB")


st.set_page_config(page_title="Arsenal Sport Content Manager", page_icon="⚽", layout="wide")
st.title("Arsenal Sport Content Manager")
st.caption("Простой MVP для вертикальной товарной карточки 4:5. Используются только ваши данные.")

with st.form("product_form"):
    uploaded_file = st.file_uploader("Фото товара", type=["jpg", "jpeg", "png", "webp"])
    left, right = st.columns(2)
    with left:
        name = st.text_input("Название товара *")
        brand = st.text_input("Бренд *")
        sku = st.text_input("Артикул")
    with right:
        sizes = st.text_input("Размеры")
        color = st.text_input("Цвет")
        description = st.text_area("Краткое описание", max_chars=160)
        features = st.text_area("Характеристики через запятую", max_chars=220)
    remove_background = st.checkbox("Убрать фон на фото", value=False)
    submitted = st.form_submit_button("Создать карточку", type="primary")

if submitted:
    if not uploaded_file or not name or not brand:
        st.error("Загрузите фото и заполните название и бренд.")
    else:
        product = {
            "name": name.strip(), "brand": brand.strip(), "sku": sku.strip(),
            "sizes": sizes.strip(), "color": color.strip(),
            "description": description.strip(), "features": features.strip(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        try:
            source_photo = Image.open(uploaded_file)
            with st.spinner("Создаём карточку..."):
                card = create_card(product, source_photo, remove_background)
            output = io.BytesIO()
            card.save(output, format="PNG")
            save_product(product)
            st.session_state["card_png"] = output.getvalue()
            st.success("Карточка создана. Данные товара сохранены в products.json.")
        except Exception as error:
            st.error(f"Не удалось обработать фото: {error}")

if "card_png" in st.session_state:
    st.image(st.session_state["card_png"], caption="Карточка Arsenal Sport", width=480)
    st.download_button(
        "Скачать карточку PNG",
        data=st.session_state["card_png"],
        file_name="arsenal-sport-card.png",
        mime="image/png",
    )
