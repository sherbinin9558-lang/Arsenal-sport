import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json
from pathlib import Path
import io

# Настройки
PRODUCTS_FILE = Path("products.json")
CARD_SIZE = (1080, 1350)
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Загрузка и сохранение данных
def load_products():
    if PRODUCTS_FILE.exists():
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_product(product):
    products = load_products()
    products.append(product)
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

# Генерация карточки
def generate_card(image, name, brand, article, sizes, color, description, specs):
    canvas = Image.new("RGB", CARD_SIZE, (30, 30, 30))
    draw = ImageDraw.Draw(canvas)

    # Вставляем фото
    if image:
        img_width, img_height = image.size
        ratio = min(800 / img_width, 800 / img_height)
        new_size = (int(img_width * ratio), int(img_height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        # Центрируем фото
        x_offset = (CARD_SIZE[0] - new_size[0]) // 2
        canvas.paste(image, (x_offset, 150))

    # Загружаем шрифты
    try:
        font_logo = ImageFont.truetype(FONT_BOLD, 45)
        font_title = ImageFont.truetype(FONT_BOLD, 80)
        font_brand = ImageFont.truetype(FONT_REGULAR, 45)
        font_text = ImageFont.truetype(FONT_REGULAR, 35)
    except:
        font_logo = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_brand = ImageFont.load_default()
        font_text = ImageFont.load_default()

    # Логотип (по центру сверху)
    logo_text = "ARSENAL SPORT"
    bbox = draw.textbbox((0, 0), logo_text, font=font_logo)
    logo_width = bbox[2] - bbox[0]
    draw.text(((CARD_SIZE[0] - logo_width) // 2, 50), logo_text, font=font_logo, fill=(255, 50, 50))

    # Бренд и Название
    draw.text((60, 1000), brand.upper(), font=font_brand, fill=(200, 200, 200))
    draw.text((60, 1050), name.upper(), font=font_title, fill=(255, 255, 255))
    
    # Описание
    draw.text((60, 1160), description, font=font_text, fill=(180, 180, 180))

    # Характеристики (слева внизу)
    y_offset = 1220
    if specs:
        draw.text((60, y_offset), f"Характеристики: {specs}", font=font_text, fill=(150, 150, 150))
        y_offset += 50
    
    draw.text((60, y_offset), f"Арт: {article} | Размеры: {sizes} | Цвет: {color}", font=font_text, fill=(150, 150, 150))

    return canvas

# Интерфейс
st.set_page_config(page_title="Arsenal Sport Content Manager", layout="wide")
st.title("Arsenal Sport Content Manager")

tab1, tab2 = st.tabs(["Создать карточку", "Каталог товаров"])

with tab1:
    st.header("Создание новой карточки товара")
    
    uploaded_file = st.file_uploader("Загрузите фото товара", type=["jpg", "jpeg", "png", "webp"])
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Название товара *")
        brand = st.text_input("Бренд *")
        article = st.text_input("Артикул")
    with col2:
        sizes = st.text_input("Размеры")
        color = st.text_input("Цвет")
        description = st.text_area("Краткое описание")
    
    specs = st.text_input("Характеристики через запятую")
    remove_bg = st.checkbox("Убрать фон на фото (временно отключено)")

    if st.button("Создать карточку", type="primary"):
        if not name or not brand:
            st.error("Пожалуйста, заполните обязательные поля: Название и Бренд.")
        else:
            with st.spinner("Генерация карточки..."):
                img = None
                if uploaded_file:
                    img = Image.open(uploaded_file).convert("RGB")
                
                card = generate_card(img, name, brand, article, sizes, color, description, specs)
                
                product_data = {
                    "name": name, "brand": brand, "article": article,
                    "sizes": sizes, "color": color, "description": description,
                    "specs": specs
                }
                save_product(product_data)
                
                st.success("Карточка создана! Данные сохранены в products.json.")
                # ИЗМЕНЕНИЕ: width=450 делает карточку компактной на экране
                st.image(card, caption="Готовая карточка", width=450)
                
                buf = io.BytesIO()
                card.save(buf, format="PNG")
                byte_im = buf.getvalue()
                st.download_button(
                    label="Скачать карточку",
                    data=byte_im,
                    file_name=f"{name.replace(' ', '_')}_card.png",
                    mime="image/png"
                )

with tab2:
    st.header("Каталог товаров")
    products = load_products()
    if not products:
        st.info("Каталог пока пуст. Создайте первую карточку!")
    else:
        for p in reversed(products):
            with st.expander(f"{p.get('brand', '')} {p.get('name', '')} (Артикул: {p.get('article', 'нет')})"):
                st.write(f"**Размеры:** {p.get('sizes', 'не указаны')}")
                st.write(f"**Цвет:** {p.get('color', 'не указан')}")
                st.write(f"**Описание:** {p.get('description', 'нет')}")
                st.write(f"**Характеристики:** {p.get('specs', 'нет')}")
