
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

    if image:
        img_width, img_height = image.size
        ratio = min(800 / img_width, 800 / img_height)
        new_size = (int(img_width * ratio), int(img_height * ratio))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        x_offset = (CARD_SIZE[0] - new_size[0]) // 2
        canvas.paste(image, (x_offset, 150))

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

    logo_text = "ARSENAL SPORT"
    bbox = draw.textbbox((0, 0), logo_text, font=font_logo)
    logo_width = bbox[2] - bbox[0]
    draw.text(((CARD_SIZE[0] - logo_width) // 2, 50), logo_text, font=font_logo, fill=(255, 50, 50))

    draw.text((60, 1000), brand.upper(), font=font_brand, fill=(200, 200, 200))
    draw.text((60, 1050), name.upper(), font=font_title, fill=(255, 255, 255))
    draw.text((60, 1160), description, font=font_text, fill=(180, 180, 180))

    y_offset = 1220
    if specs:
        draw.text((60, y_offset), f"Характеристики: {specs}", font=font_text, fill=(150, 150, 150))
        y_offset += 50
    
    draw.text((60, y_offset), f"Арт: {article} | Размеры: {sizes} | Цвет: {color}", font=font_text, fill=(150, 150, 150))

    return canvas

# Интерфейс
st.set_page_config(page_title="Arsenal Sport Content Manager", layout="wide")
st.title("Arsenal Sport Content Manager")

# ТЕПЕРЬ ЧЕТЫРЕ ВКЛАДКИ
tab1, tab2, tab3, tab4 = st.tabs(["Создать карточку", "Каталог товаров", "Тексты для соцсетей", "Идеи для Reels/Stories"])

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

with tab3:
    st.header("Генератор текстов для соцсетей")
    st.write("Выберите товар из каталога, и мы сгенерируем для него готовые тексты.")
    
    products = load_products()
    if not products:
        st.info("Сначала создайте хотя бы один товар во вкладке 'Создать карточку'.")
    else:
        product_names = [f"{p.get('brand', '')} {p.get('name', '')} ({p.get('article', '')})" for p in products]
        selected_idx = st.selectbox("Выберите товар", range(len(product_names)), format_func=lambda x: product_names[x], key="sb_text")
        
        if st.button("Сгенерировать тексты"):
            p = products[selected_idx]
            
            insta_text = f"""🔥 НОВИНКА В ARSENAL SPORT! 🔥

Представляем вам {p.get('name', '')} от {p.get('brand', '')}!

📝 {p.get('description', '')}
📏 Размеры: {p.get('sizes', 'уточняйте')}
🎨 Цвет: {p.get('color', 'уточняйте')}
⚙️ Характеристики: {p.get('specs', '')}

🛒 Закажите прямо сейчас в нашем магазине!
📩 Пишите в личные сообщения для заказа.

#arsenal_sport #спорт #экипировка #{p.get('brand', '').lower()} #новинка"""
            
            tg_text = f"""🏆 **Новое поступление в Arsenal Sport!**

**{p.get('name', '')}** от бренда **{p.get('brand', '')}**

{p.get('description', '')}

**Характеристики:**
• Артикул: {p.get('article', 'нет')}
• Размеры: {p.get('sizes', 'уточняйте')}
• Цвет: {p.get('color', 'уточняйте')}
• Особенности: {p.get('specs', '')}

📍 Заходите в наш магазин или пишите для оформления заказа!"""
            
            st.subheader("Текст для Instagram")
            st.text_area("Скопируйте текст", insta_text, height=200, key="insta")
            st.download_button(
                label="Скачать текст для Instagram",
                data=insta_text,
                file_name=f"{p.get('name', 'товар').replace(' ', '_')}_instagram.txt",
                mime="text/plain"
            )
            
            st.subheader("Текст для Telegram")
            st.text_area("Скопируйте текст", tg_text, height=200, key="tg")
            st.download_button(
                label="Скачать текст для Telegram",
                data=tg_text,
                file_name=f"{p.get('name', 'товар').replace(' ', '_')}_telegram.txt",
                mime="text/plain"
            )

with tab4:
    st.header("Генератор идей и сценариев для Reels и Stories")
    st.write("Выберите товар, и мы предложим вам варианты сценариев для коротких видео.")
    
    products = load_products()
    if not products:
        st.info("Сначала создайте хотя бы один товар во вкладке 'Создать карточку'.")
    else:
        product_names = [f"{p.get('brand', '')} {p.get('name', '')} ({p.get('article', '')})" for p in products]
        selected_idx = st.selectbox("Выберите товар", range(len(product_names)), format_func=lambda x: product_names[x], key="sb_reels")
        
        if st.button("Сгенерировать идеи для Reels/Stories"):
            p = products[selected_idx]
            name = p.get('name', '')
            brand = p.get('brand', '')
            desc = p.get('description', '')
            
            # Генерация идей
            ideas = f"""💡 ИДЕИ ДЛЯ REELS И STORIES:

1. **Распаковка (Unboxing):** Крупным планом показать товар, рассказать о материалах и качестве. Текст на экране: "Новинка от {brand}!"
2. **Обзор (Review):** Надеть/примерить товар, показать его в движении. Рассказать о посадке и комфорте. Текст: "Идеально для тренировок".
3. **Стилизация (Styling):** Показать 3 разных образа с этим товаром. Текст: "С чем носить {name}?"
4. **Сравнение (Before/After):** Показать старую вещь и новую, подчеркнуть преимущества. Текст: "Почувствуйте разницу".
5. **Вопрос-Ответ (Q&A):** Ответить на частые вопросы о товаре (размеры, уход). Текст: "Отвечаем на ваши вопросы"."""

            # Генерация сценария
            script = f"""🎬 СЦЕНАРИЙ ДЛЯ REELS (30 секунд):

**Кадр 1 (0-5 сек):** Общий план. Товар лежит на столе. 
*Текст на экране:* "Смотрите, какая новинка!"
*Голос/Текст:* "Встречайте {name} от {brand}!"

**Кадр 2 (5-15 сек):** Крупный план. Показать детали, текстуру, логотип.
*Текст на экране:* "Качество, которое видно"
*Голос/Текст:* "{desc}"

**Кадр 3 (15-25 сек):** Человек держит товар или примеряет его.
*Текст на экране:* "Идеально подходит для..."
*Голос/Текст:* "Доступные размеры: {p.get('sizes', 'уточняйте')}. Цвет: {p.get('color', 'уточняйте')}."

**Кадр 4 (25-30 сек):** Призыв к действию (CTA).
*Текст на экране:* "Заказывайте в Arsenal Sport!"
*Голос/Текст:* "Ссылка в шапке профиля!""" 
            
            st.subheader("Идеи для Reels и Stories")
            st.text_area("Скопируйте идеи", ideas, height=250, key="ideas")
            st.download_button(
                label="Скачать идеи",
                data=ideas,
                file_name=f"{name.replace(' ', '_')}_reels_ideas.txt",
                mime="text/plain"
            )
            
            st.subheader("Готовый сценарий для Reels")
            st.text_area("Скопируйте сценарий", script, height=300, key="script")
            st.download_button(
                label="Скачать сценарий",
                data=script,
                file_name=f"{name.replace(' ', '_')}_reels_script.txt",
                mime="text/plain"
            ) 
