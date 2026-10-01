import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json, io, datetime, csv
from pathlib import Path

# ==================== КОНФИГУРАЦИЯ ====================
PRODUCTS_FILE = Path("products.json")
CONTENT_PLAN_FILE = Path("content_plan.json")
LOGO_FILE = Path("logo.png")
CARD_SIZE = (1080, 1350)
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

CATEGORIES = ["Футболка", "Кроссовки", "Спортивный костюм", "Аксессуары", "Инвентарь", "Другое"]
TONES = ["Официальный", "Дружеский", "Продающий"]
PLATFORMS = ["Instagram", "Telegram", "VK", "Другое"]
CONTENT_TYPES = ["Пост", "Reels", "Stories", "Карусель"]
STATUSES = ["Идея", "В работе", "Готово", "Опубликовано"]
PRIORITIES = ["Обычный", "Высокий", "Срочно"]

TEMPLATES = {
    "Тёмный":     {"bg": (18,18,18),    "text": (255,255,255), "sec": (180,180,180), "accent": (204,0,0)},
    "Светлый":    {"bg": (245,245,245), "text": (30,30,30),    "sec": (100,100,100), "accent": (204,0,0)},
    "Красный":    {"bg": (204,0,0),     "text": (255,255,255), "sec": (255,220,220), "accent": (255,255,255)},
    "Минимализм": {"bg": (255,255,255), "text": (20,20,20),    "sec": (130,130,130), "accent": (0,0,0)},
    "Спортивный": {"bg": (25,40,60),    "text": (255,255,255), "sec": (180,200,220), "accent": (0,180,255)},
    "Премиум":    {"bg": (15,15,15),    "text": (212,175,55),  "sec": (200,200,200), "accent": (212,175,55)},
}

CATEGORY_EMOJI = {
    "Футболка": "👕", "Кроссовки": "👟", "Спортивный костюм": "🩳",
    "Аксессуары": "🧢", "Инвентарь": "🏋️", "Другое": "📦"
}

# ==================== ДАННЫЕ ====================
def load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_products(): return load_json(PRODUCTS_FILE, [])
def save_products(p): save_json(PRODUCTS_FILE, p)
def add_product(prod):
    p = load_products(); p.append(prod); save_products(p)
def update_product(i, prod):
    p = load_products()
    if 0 <= i < len(p): p[i] = prod; save_products(p)
def delete_product(i):
    p = load_products()
    if 0 <= i < len(p): p.pop(i); save_products(p)

def load_plan(): return load_json(CONTENT_PLAN_FILE, [])
def save_plan(pl): save_json(CONTENT_PLAN_FILE, pl)
def add_plan(item):
    p = load_plan(); p.append(item); save_plan(p)
def update_plan(i, item):
    p = load_plan()
    if 0 <= i < len(p): p[i] = item; save_plan(p)
def delete_plan(i):
    p = load_plan()
    if 0 <= i < len(p): p.pop(i); save_plan(p)

def get_logo():
    if LOGO_FILE.exists():
        try: return Image.open(LOGO_FILE).convert("RGBA")
        except Exception: return None
    return None

def save_logo(f):
    img = Image.open(f).convert("RGBA")
    img.save(LOGO_FILE)

# ==================== КАРТОЧКА ====================
def get_font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)
    except Exception:
        return ImageFont.load_default()

def fit_font(draw, text, max_w, max_size=80, min_size=38):
    size = max_size
    while size > min_size:
        f = get_font(size, True)
        bbox = draw.textbbox((0, 0), text, font=f)
        if (bbox[2] - bbox[0]) <= max_w:
            return f
        size -= 3
    return get_font(min_size, True)

def draw_centered(draw, text, font, fill, y, w):
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text(((w - (bbox[2] - bbox[0])) // 2, y), text, font=font, fill=fill)

def generate_card(image, name, brand, article, sizes, color, description, specs, category, template):
    t = TEMPLATES.get(template, TEMPLATES["Тёмный"])
    canvas = Image.new("RGB", CARD_SIZE, t["bg"])
    draw = ImageDraw.Draw(canvas)

    logo_img = get_logo()
    if logo_img:
        logo_w = 450
        ratio = logo_w / logo_img.width
        lr = logo_img.resize((logo_w, int(logo_img.height * ratio)), Image.Resampling.LANCZOS)
        canvas.paste(lr, ((CARD_SIZE[0] - logo_w) // 2, 40), lr)
    else:
        draw_centered(draw, "ARSENAL SPORT", get_font(50, True), t["accent"], 55, CARD_SIZE[0])

    draw.line([(100, 160), (CARD_SIZE[0] - 100, 160)], fill=t["accent"], width=3)

    fcat = get_font(30, True)
    ctext = f"{CATEGORY_EMOJI.get(category,'📦')} {category.upper()}"
    bb = draw.textbbox((0, 0), ctext, font=fcat)
    draw.text((CARD_SIZE[0] - (bb[2] - bb[0]) - 60, 185), ctext, font=fcat, fill=t["sec"])

    if image:
        iw, ih = image.size
        ratio = min(760 / iw, 760 / ih)
        ns = (int(iw * ratio), int(ih * ratio))
        image = image.resize(ns, Image.Resampling.LANCZOS)
        canvas.paste(image, ((CARD_SIZE[0] - ns[0]) // 2, 260))

    draw.text((60, 1050), brand.upper(), font=get_font(42), fill=t["sec"])

    nu = name.upper()
    ft = fit_font(draw, nu, CARD_SIZE[0] - 120)
    draw.text((60, 1100), nu, font=ft, fill=t["text"])

    desc = description[:90] + ("..." if len(description) > 90 else "")
    draw.text((60, 1200), desc, font=get_font(30), fill=t["sec"])

    fs = get_font(26)
    draw.text((60, 1255), f"Арт: {article}  |  Размеры: {sizes}  |  Цвет: {color}", font=fs, fill=t["sec"])
    if specs:
        ss = specs[:75] + ("..." if len(specs) > 75 else "")
        draw.text((60, 1295), ss, font=fs, fill=t["sec"])

    return canvas

# ==================== ТЕКСТЫ ====================
def make_hashtags(name, brand, category):
    base = ["#arsenal_sport", "#спорт", "#экипировка", "#новинка"]
    extra = {
        "Футболка": ["#футболка", "#tshirt"],
        "Кроссовки": ["#кроссовки", "#sneakers"],
        "Спортивный костюм": ["#спорткостюм", "#sportswear"],
        "Аксессуары": ["#аксессуары", "#accessories"],
        "Инвентарь": ["#инвентарь", "#gym"],
        "Другое": ["#спорттовары"],
    }
    tags = base + extra.get(category, ["#спорттовары"])
    if brand:
        tags.append(f"#{brand.lower().replace(' ', '')}")
    return " ".join(tags)

def gen_instagram(p, tone):
    n, b = p.get('name',''), p.get('brand','')
    tags = make_hashtags(n, b, p.get('category','Другое'))
    emoji = CATEGORY_EMOJI.get(p.get('category','Другое'), '📦')
    if tone == "Официальный":
        head = f"Представляем новинку от {b}"
    elif tone == "Дружеский":
        head = "Друзья, у нас отличные новости! 🎉"
    else:
        head = "🔥 ТОЛЬКО СЕЙЧАС! Специальное предложение!"
    return f"""{head}

{emoji} {n} от {b}

📝 {p.get('description','')}
📏 Размеры: {p.get('sizes','уточняйте')}
🎨 Цвет: {p.get('color','уточняйте')}
⚙️ {p.get('specs','')}

🛒 Закажите прямо сейчас!
📩 Пишите в личные сообщения.

{tags}"""

def gen_telegram(p, tone):
    n, b = p.get('name',''), p.get('brand','')
    emoji = CATEGORY_EMOJI.get(p.get('category','Другое'), '📦')
    head = {"Официальный": "🏆 Новое поступление в Arsenal Sport",
            "Дружеский": "🎉 Ребята, новинка уже в наличии!",
            "Продающий": "🔥 СУПЕРПРЕДЛОЖЕНИЕ!"}.get(tone, "🏆 Новинка")
    return f"""{head}

{emoji} {n} от бренда {b}

{p.get('description','')}

Характеристики:
• Артикул: {p.get('article','нет')}
• Размеры: {p.get('sizes','уточняйте')}
• Цвет: {p.get('color','уточняйте')}
• Особенности: {p.get('specs','')}

📍 Заходите в магазин или пишите для заказа!"""

def gen_vk(p, tone):
    n, b = p.get('name',''), p.get('brand','')
    return f"""🏆 {n} от {b}

{p.get('description','')}

📏 Размеры: {p.get('sizes','уточняйте')}
🎨 Цвет: {p.get('color','уточняйте')}
⚙️ {p.get('specs','')}

📍 Заказать: напишите нам в сообщения сообщества.
{make_hashtags(n, b, p.get('category','Другое'))}"""

# ==================== ИНТЕРФЕЙС ====================
st.set_page_config(page_title="Arsenal Sport Content Manager", layout="wide", page_icon="🏆")

with st.sidebar:
    st.title("🏆 Arsenal Sport")
    st.caption("Content Manager v2.1")
    dark_mode = st.toggle("🌙 Тёмная тема", value=True)
    st.markdown("---")
    st.metric("📦 Товаров", len(load_products()))
    st.metric("📅 Записей в плане", len(load_plan()))
    st.markdown("---")
    st.caption(f"Сегодня: {datetime.date.today().strftime('%d.%m.%Y')}")

if dark_mode:
    bg_css = "body {background: #0e1117;}"
else:
    bg_css = "body {background: #ffffff;}"

st.markdown(f"""
<style>
{bg_css}
.main-title {{font-size: 2.5rem; font-weight: 800; color: #cc0000; text-align: center; margin-bottom: 0;}}
.subtitle {{text-align: center; color: #888; margin-top: 0; font-size: 0.9rem;}}
.stat-box {{background: linear-gradient(135deg, #cc0000 0%, #8b0000 100%); color: white; padding: 20px; border-radius: 12px; text-align: center; margin: 5px;}}
.stat-number {{font-size: 2.5rem; font-weight: 900; margin: 0;}}
.stat-label {{font-size: 0.9rem; opacity: 0.9; margin: 0;}}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🏆 ARSENAL SPORT</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Content Manager — управление контентом магазина</p>', unsafe_allow_html=True)
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📸 Создать", "📦 Каталог", "📱 Тексты", "🎬 Reels",
    "📅 План", "📊 Статистика", "⚙️ Настройки"
])

# ========== 1: СОЗДАТЬ КАРТОЧКУ ==========
with tab1:
    st.header("Создание карточки товара")
    up = st.file_uploader("📷 Фото товара", type=["jpg","jpeg","png","webp"])
    c1, c2, c3 = st.columns(3)
    with c1:
        name = st.text_input("Название *")
        brand = st.text_input("Бренд *")
        article = st.text_input("Артикул")
    with c2:
        sizes = st.text_input("Размеры")
        color = st.text_input("Цвет")
        category = st.selectbox("Категория", CATEGORIES)
    with c3:
        description = st.text_area("Описание", height=100)
        template = st.selectbox("🎨 Шаблон", list(TEMPLATES.keys()))
    specs = st.text_input("Характеристики через запятую")

    if st.button("🎨 Создать карточку", type="primary"):
        if not name or not brand:
            st.error("Заполните: Название и Бренд")
        else:
            with st.spinner("Генерация..."):
                img = Image.open(up).convert("RGB") if up else None
                card = generate_card(img, name, brand, article, sizes, color, description, specs, category, template)
                add_product({
                    "name": name, "brand": brand, "article": article,
                    "sizes": sizes, "color": color, "description": description,
                    "specs": specs, "category": category,
                    "date_added": str(datetime.date.today())
                })
                st.success("✅ Карточка создана!")
                st.image(card, caption="Готово (1080×1350)", width=400)
                buf = io.BytesIO()
                card.save(buf, format="PNG")
                st.download_button("⬇️ Скачать карточку", buf.getvalue(),
                    file_name=f"{name.replace(' ','_')}_card.png", mime="image/png")

# ========== 2: КАТАЛОГ ==========
with tab2:
    st.header("Каталог товаров")
    products = load_products()
    if not products:
        st.info("Каталог пуст.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            search = st.text_input("🔍 Поиск")
        with c2:
            cat_filter = st.selectbox("Категория", ["Все"] + CATEGORIES)
        with c3:
            sort_by = st.selectbox("Сортировка", ["Сначала новые","Сначала старые","По названию","По бренду"])

        filtered = []
        for i, p in enumerate(products):
            if search and search.lower() not in (p.get('name','') + p.get('brand','') + p.get('article','')).lower():
                continue
            if cat_filter != "Все" and p.get('category','Другое') != cat_filter:
                continue
            filtered.append((i, p))

        if sort_by == "Сначала старые":
            filtered = sorted(filtered, key=lambda x: x[0])
        elif sort_by == "По названию":
            filtered = sorted(filtered, key=lambda x: x[1].get('name','').lower())
        elif sort_by == "По бренду":
            filtered = sorted(filtered, key=lambda x: x[1].get('brand','').lower())
        else:
            filtered = sorted(filtered, key=lambda x: x[0], reverse=True)

        st.caption(f"Найдено: {len(filtered)} из {len(products)}")
        st.markdown("---")

        for real_i, p in filtered:
            with st.expander(f"{CATEGORY_EMOJI.get(p.get('category',''),'📦')} {p.get('brand','')} {p.get('name','')} — {p.get('article','')}"):
                edit = st.toggle("✏️ Редактировать", key=f"edit_{real_i}")
                if edit:
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        nn = st.text_input("Название", p.get('name',''), key=f"n_{real_i}")
                        nb = st.text_input("Бренд", p.get('brand',''), key=f"b_{real_i}")
                        na = st.text_input("Артикул", p.get('article',''), key=f"a_{real_i}")
                    with ec2:
                        ns = st.text_input("Размеры", p.get('sizes',''), key=f"s_{real_i}")
                        nc = st.text_input("Цвет", p.get('color',''), key=f"c_{real_i}")
                        ncat = st.selectbox("Категория", CATEGORIES,
                            index=CATEGORIES.index(p.get('category','Другое')) if p.get('category','Другое') in CATEGORIES else 5,
                            key=f"ct_{real_i}")
                    nd = st.text_area("Описание", p.get('description',''), key=f"d_{real_i}")
                    nsp = st.text_input("Характеристики", p.get('specs',''), key=f"sp_{real_i}")
                    if st.button("💾 Сохранить", key=f"save_{real_i}"):
                        update_product(real_i, {
                            "name": nn, "brand": nb, "article": na, "sizes": ns,
                            "color": nc, "description": nd, "specs": nsp,
                            "category": ncat, "date_added": p.get('date_added', str(datetime.date.today()))
                        })
                        st.success("Обновлено!")
                        st.rerun()
                else:
                    st.write(f"**Размеры:** {p.get('sizes','—')}")
                    st.write(f"**Цвет:** {p.get('color','—')}")
                    st.write(f"**Описание:** {p.get('description','—')}")
                    st.write(f"**Характеристики:** {p.get('specs','—')}")
                    st.caption(f"Добавлено: {p.get('date_added','—')}")

                if st.button("🗑️ Удалить", key=f"del_{real_i}"):
                    delete_product(real_i)
                    st.rerun()

# ========== 3: ТЕКСТЫ С ПУБЛИКАЦИЕЙ ==========
with tab3:
    st.header("Тексты для соцсетей")
    products = load_products()
    if not products:
        st.info("Сначала создайте товар.")
    else:
        names = [f"{p.get('brand','')} {p.get('name','')} ({p.get('article','')})" for p in products]
        idx = st.selectbox("Товар", range(len(names)), format_func=lambda x: names[x])
        tone = st.radio("Тональность", TONES, horizontal=True)

        if st.button("✨ Сгенерировать", type="primary"):
            p = products[idx]
            insta = gen_instagram(p, tone)
            tg = gen_telegram(p, tone)
            vk = gen_vk(p, tone)

            st.markdown("---")
            st.subheader("📸 Instagram")
            st.text_area("Текст поста", insta, height=300, key="i_out")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Скачать текст", insta,
                    file_name=f"{p.get('name','item')}_insta.txt", mime="text/plain")
            with c2:
                st.markdown(
                    f'<a href="https://www.instagram.com/" target="_blank" '
                    f'style="display:inline-block;padding:10px 20px;background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888);'
                    f'color:white;border-radius:6px;text-decoration:none;font-weight:600;">📤 Открыть Instagram</a>',
                    unsafe_allow_html=True
                )
            st.caption("ℹ️ Скопируйте текст, откройте Instagram и вставьте его в пост. Карточку скачайте выше.")

            st.markdown("---")
            st.subheader("✈️ Telegram")
            st.text_area("Текст поста", tg, height=300, key="t_out")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Скачать текст", tg,
                    file_name=f"{p.get('name','item')}_tg.txt", mime="text/plain")
            with c2:
                tg_link = f"https://t.me/share/url?url=&text={tg}"
                st.markdown(
                    f'<a href="{tg_link}" target="_blank" '
                    f'style="display:inline-block;padding:10px 20px;background:#229ED9;'
                    f'color:white;border-radius:6px;text-decoration:none;font-weight:600;">📤 Отправить в Telegram</a>',
                    unsafe_allow_html=True
                )

            st.markdown("---")
            st.subheader("🅥 ВКонтакте")
            st.text_area("Текст поста", vk, height=200, key="v_out")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ Скачать текст", vk,
                    file_name=f"{p.get('name','item')}_vk.txt", mime="text/plain")
            with c2:
                vk_link = f"https://vk.com/share.php?url=&title={p.get('name','')}&description={vk}"
                st.markdown(
                    f'<a href="{vk_link}" target="_blank" '
                    f'style="display:inline-block;padding:10px 20px;background:#0077FF;'
                    f'color:white;border-radius:6px;text-decoration:none;font-weight:600;">📤 Отправить в VK</a>',
                    unsafe_allow_html=True
                )

# ========== 4: REELS & STORIES ==========
with tab4:
    st.header("Reels & Stories")
    products = load_products()
    if not products:
        st.info("Сначала создайте товар.")
    else:
        names = [f"{p.get('brand','')} {p.get('name','')}" for p in products]
        idx = st.selectbox("Товар", range(len(names)), format_func=lambda x: names[x], key="r_sel")

        if st.button("🎬 Сгенерировать", type="primary"):
            p = products[idx]
            n, b, d = p.get('name',''), p.get('brand',''), p.get('description','')

            ideas = f"""💡 ИДЕИ ДЛЯ REELS:

1. 📦 Распаковка — показать товар крупным планом
2. 👕 Обзор — надеть и показать в движении
3. 🎨 Стилизация — 3 образа с товаром
4. ⚖️ Сравнение — до/после
5. ❓ Q&A — ответы на вопросы о {n}"""

            script = f"""🎬 СЦЕНАРИЙ REELS (30 сек):

[0-5 сек] Открывашка
📹 Общий план товара
💬 "Смотрите, какая новинка!"
🎙️ "Встречайте {n} от {b}!"

[5-15 сек] Детали
📹 Крупный план
💬 "Качество, которое видно"
🎙️ "{d}"

[15-25 сек] Примерка
📹 Человек с товаром
💬 "Идеально подходит для..."
🎙️ "Размеры: {p.get('sizes','уточняйте')}. Цвет: {p.get('color','уточняйте')}"

[25-30 сек] CTA
📹 Логотип Arsenal Sport
💬 "Заказывайте!"
🎙️ "Ссылка в шапке профиля!"

🎵 Энергичный спортивный трек"""

            stories = f"""📱 ИДЕИ STORIES:

1. Опрос: "Какой цвет лучше?"
2. Слайдер: "Оцените от 1 до 10"
3. Q&A: "Задайте вопрос о {n}"
4. Обратный отсчёт до старта
5. Ссылка на товар"""

            st.subheader("💡 Идеи")
            st.text_area("", ideas, height=200, key="id_out")
            st.download_button("⬇️ Идеи", ideas, file_name=f"{n}_ideas.txt")

            st.subheader("🎬 Сценарий")
            st.text_area("", script, height=350, key="sc_out")
            st.download_button("⬇️ Сценарий", script, file_name=f"{n}_script.txt")

            st.subheader("📱 Stories")
            st.text_area("", stories, height=150, key="st_out")
            st.download_button("⬇️ Stories", stories, file_name=f"{n}_stories.txt")

# ========== 5: КОНТЕНТ-ПЛАН ==========
with tab5:
    st.header("Контент-план")
    products = load_products()
    if not products:
        st.info("Сначала создайте товар.")
    else:
        with st.form("plan_f", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                pd = st.date_input("Дата")
                pl = st.selectbox("Платформа", PLATFORMS)
            with c2:
                pn = [f"{p.get('brand','')} {p.get('name','')}" for p in products]
                sp = st.selectbox("Товар", pn)
                ct = st.selectbox("Тип", CONTENT_TYPES)
            with c3:
                sts = st.selectbox("Статус", STATUSES)
                pr = st.selectbox("Приоритет", PRIORITIES)
            idea = st.text_area("Идея / текст")
            if st.form_submit_button("📌 Добавить"):
                add_plan({"date": str(pd), "platform": pl, "product": sp,
                          "type": ct, "idea": idea, "status": sts, "priority": pr})
                st.success("Добавлено!")
                st.rerun()

        st.markdown("---")
        plan = load_plan()
        if not plan:
            st.info("План пуст.")
        else:
            st.subheader("📅 По неделям")
            weeks = {}
            for i, item in enumerate(plan):
                try:
                    d = datetime.datetime.strptime(item.get('date',''), '%Y-%m-%d').date()
                    wk = d.isocalendar()[1]
                    weeks.setdefault(wk, []).append((i, item))
                except Exception:
                    weeks.setdefault(0, []).append((i, item))

            for wk in sorted(weeks.keys()):
                with st.expander(f"Неделя {wk} ({len(weeks[wk])} записей)"):
                    for i, item in weeks[wk]:
                        pr_icon = {"Обычный":"⚪","Высокий":"🟡","Срочно":"🔴"}.get(item.get('priority','Обычный'),'⚪')
                        st.write(f"{pr_icon} **{item.get('date','')}** | {item.get('platform','')} | {item.get('type','')} | _{item.get('status','')}_")
                        st.write(f"   {item.get('product','')}: {item.get('idea','')}")

            st.markdown("---")
            csv_buf = io.StringIO()
            writer = csv.writer(csv_buf)
            writer.writerow(["Дата","Платформа","Товар","Тип","Статус","Приоритет","Идея"])
            for item in plan:
                writer.writerow([item.get('date',''), item.get('platform',''),
                    item.get('product',''), item.get('type',''), item.get('status',''),
                    item.get('priority','Обычный'), item.get('idea','')])
            st.download_button("⬇️ Экспорт в Excel (CSV)", csv_buf.getvalue(),
                file_name=f"content_plan_{datetime.date.today()}.csv", mime="text/csv")

            st.subheader("Управление записями")
            for i, item in enumerate(reversed(plan)):
                ri = len(plan) - 1 - i
                with st.expander(f"{item.get('date','')} | {item.get('product','')}"):
                    st.write(f"**Идея:** {item.get('idea','')}")
                    cs = item.get('status','Идея')
                    ns = st.selectbox("Статус", STATUSES, index=STATUSES.index(cs) if cs in STATUSES else 0, key=f"st_{ri}")
                    if ns != cs:
                        item['status'] = ns
                        update_plan(ri, item)
                        st.rerun()
                    if st.button("🗑️ Удалить", key=f"dp_{ri}"):
                        delete_plan(ri)
                        st.rerun()

# ========== 6: СТАТИСТИКА ==========
with tab6:
    st.header("📊 Статистика")
    products = load_products()
    plan = load_plan()

    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="stat-box"><p class="stat-number">{len(products)}</p><p class="stat-label">товаров</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="stat-box"><p class="stat-number">{len(plan)}</p><p class="stat-label">записей в плане</p></div>', unsafe_allow_html=True)
    pub = len([p for p in plan if p.get('status') == 'Опубликовано'])
    c3.markdown(f'<div class="stat-box"><p class="stat-number">{pub}</p><p class="stat-label">опубликовано</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    if products:
        st.subheader("📦 Категории")
        cc = {}
        for p in products:
            c = p.get('category','Другое')
            cc[c] = cc.get(c,0) + 1
        for c, n in sorted(cc.items(), key=lambda x: -x[1]):
            st.write(f"{CATEGORY_EMOJI.get(c,'📦')} **{c}:** {n}")

    if plan:
        st.subheader("📅 Статусы")
        sc = {}
        for item in plan:
            s = item.get('status','Идея')
            sc[s] = sc.get(s,0) + 1
        for s, n in sorted(sc.items(), key=lambda x: -x[1]):
            st.write(f"**{s}:** {n}")

# ========== 7: НАСТРОЙКИ ==========
with tab7:
    st.header("⚙️ Настройки")

    st.subheader("🖼️ Логотип магазина")
    st.caption("Загрузите PNG-файл с прозрачным фоном — он будет появляться на всех карточках.")
    logo_up = st.file_uploader("Загрузить логотип", type=["png"], key="logo")
    if logo_up:
        save_logo(logo_up)
        st.success("Логотип сохранён!")
        st.image(LOGO_FILE, width=200)
    elif LOGO_FILE.exists():
        st.image(LOGO_FILE, width=200)
        if st.button("🗑️ Удалить логотип"):
            LOGO_FILE.unlink()
            st.rerun()

    st.markdown("---")

    st.subheader("💾 Резервное копирование")
    products = load_products()
    plan = load_plan()
    backup = {"products": products, "content_plan": plan, "date": str(datetime.date.today())}
    st.download_button("⬇️ Скачать все данные (JSON)",
        json.dumps(backup, ensure_ascii=False, indent=2),
        file_name=f"arsenal_backup_{datetime.date.today()}.json", mime="application/json")

    st.markdown("---")
    st.subheader("⚠️ Опасная зона")
    if st.button("🗑️ Очистить каталог товаров"):
        save_products([])
        st.success("Каталог очищен!")
        st.rerun()
    if st.button("🗑️ Очистить контент-план"):
        save_plan([])
        st.success("План очищен!")
        st.rerun()

st.markdown("---")
st.caption("Arsenal Sport Content Manager v2.1 — MVP. Все данные хранятся в облаке.")
