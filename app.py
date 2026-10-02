
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json, io, datetime, csv, requests, base64, re
from pathlib import Path
from max_features import product_search, catalog_metrics, auto_content_bundle, planner_suggestions, knowledge_answer
from crm_core import create_lead, crm_metrics, load_leads, update_lead, add_lead_interaction, set_customer_profile, STATUSES as CRM_STATUSES

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
    "Графит":      {"bg": (15,18,24),  "text": (245,247,250), "sec": (165,172,184), "accent": (137,125,255)},
    "Светлый":     {"bg": (245,247,250), "text": (25,29,38), "sec": (105,112,125), "accent": (111,104,214)},
    "Минимализм":  {"bg": (250,251,253), "text": (25,29,38), "sec": (110,116,128), "accent": (111,104,214)},
    "Спортивный":  {"bg": (18,25,36),  "text": (245,247,250), "sec": (166,181,201), "accent": (105,164,235)},
    "Премиум":     {"bg": (18,20,27),  "text": (239,242,247), "sec": (177,184,198), "accent": (137,125,255)},
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
    t = TEMPLATES.get(template, TEMPLATES["Графит"])
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
    category = p.get('category','Другое')
    desc = p.get('description','').strip()
    specs = p.get('specs','').strip()
    sizes = p.get('sizes','уточняйте')
    color = p.get('color','уточняйте')
    tags = make_hashtags(n, b, category)
    emoji = CATEGORY_EMOJI.get(category, '📦')
    heads = {
        "Официальный": "Новая позиция в Arsenal Sport — " + n,
        "Дружеский": "🔥 Забирайте новинку: " + n,
        "Продающий": "🔥 " + n + " — экипировка для тех, кто выбирает по делу!"
    }
    return heads.get(tone, heads["Официальный"]) + f"""

{emoji} {n}
🏷️ Бренд: {b}
🎨 Цвет: {color}
📏 Размеры: {sizes}

{desc}

⚙️ {specs}

📩 Напишите нам в сообщения Arsenal Sport — поможем подобрать размер и оформить заказ.

{tags}"""

def gen_telegram(p, tone):
    n, b = p.get('name',''), p.get('brand','')
    category = p.get('category','Другое')
    desc = p.get('description','').strip()
    specs = p.get('specs','').strip()
    sizes = p.get('sizes','уточняйте')
    color = p.get('color','уточняйте')
    emoji = CATEGORY_EMOJI.get(category, '📦')
    heads = {
        "Официальный": "🏆 Новое поступление в Arsenal Sport",
        "Дружеский": "🎉 Ребята, смотрите, что приехало!",
        "Продающий": "🔥 НОВИНКА В ARSENAL SPORT"
    }
    return f"""{heads.get(tone, heads["Официальный"])}

{emoji} {n}
Бренд: {b}

{desc}

Характеристики:
• Размеры: {sizes}
• Цвет: {color}
• Особенности: {specs}

📩 Для заказа напишите нам в сообщения. Подскажем наличие и поможем подобрать вариант."""

def gen_vk(p, tone):
    n, b = p.get('name',''), p.get('brand','')
    desc = p.get('description','').strip()
    sizes = p.get('sizes','уточняйте')
    color = p.get('color','уточняйте')
    specs = p.get('specs','').strip()
    return f"""🔥 {n} — {b}

{desc}

📏 Размеры: {sizes}
🎨 Цвет: {color}
⚙️ Характеристики: {specs}

📩 Чтобы заказать товар или уточнить наличие, напишите нам в сообщения сообщества.
{make_hashtags(n, b, p.get('category','Другое'))}"""

# ==================== ПУБЛИКАЦИЯ В TELEGRAM ====================
def publish_to_telegram(image_bytes, caption):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        channel = st.secrets["TELEGRAM_CHANNEL"]
        if not channel.startswith("@"):
            channel = "@" + channel
        api_url = f"https://api.telegram.org/bot{token}/sendPhoto"
        files = {"photo": ("card.png", image_bytes, "image/png")}
        data = {"chat_id": channel, "caption": caption[:1024]}
        resp = requests.post(api_url, files=files, data=data, timeout=60)
        if resp.status_code == 200:
            return True, "Пост успешно опубликован!"
        else:
            return False, f"Ошибка {resp.status_code}: {resp.text}"
    except KeyError as e:
        return False, f"Не найден секрет: {e}."
    except Exception as e:
        return False, f"Ошибка публикации: {e}"

# ==================== ПУБЛИКАЦИЯ REELS ====================
def publish_reel_to_telegram(video_bytes, caption):
    try:
        token = st.secrets["TELEGRAM_TOKEN"]
        channel = st.secrets["TELEGRAM_CHANNEL"]
        if not str(channel).startswith("@"):
            channel = "@" + str(channel)
        api_url = f"https://api.telegram.org/bot{token}/sendVideo"
        files = {"video": ("reel.mp4", video_bytes, "video/mp4")}
        data = {
            "chat_id": channel,
            "caption": caption[:1024],
            "supports_streaming": "true",
        }
        resp = requests.post(api_url, files=files, data=data, timeout=120)
        if resp.status_code == 200:
            return True, "Reels опубликован в Telegram!"
        return False, f"Ошибка Telegram {resp.status_code}: {resp.text}"
    except KeyError as e:
        return False, f"Не найден секрет: {e}."
    except Exception as e:
        return False, f"Ошибка Telegram: {e}"

def publish_reel_to_vk(video_bytes, caption):
    try:
        token = st.secrets["VK_ACCESS_TOKEN"]
        owner_id = int(st.secrets["VK_OWNER_ID"])
        api_version = str(st.secrets.get("VK_API_VERSION", "5.199"))

        save_url = "https://api.vk.com/method/video.save"
        params = {
            "access_token": token,
            "v": api_version,
            "name": "Arsenal Sport Reels",
            "description": caption[:4096],
            "is_private": 0,
            "wallpost": 1,
            "owner_id": owner_id,
        }
        resp = requests.post(save_url, data=params, timeout=60)
        data = resp.json()

        if "error" in data:
            return False, f"Ошибка VK: {data['error'].get('error_msg', data['error'])}"

        video = data.get("response", {})
        upload_url = video.get("upload_url")
        if not upload_url:
            return False, "VK не вернул upload_url."

        upload = requests.post(
            upload_url,
            files={"video_file": ("reel.mp4", video_bytes, "video/mp4")},
            timeout=180,
        )
        upload_data = upload.json()
        if "error" in upload_data:
            return False, f"Ошибка загрузки VK: {upload_data['error']}"

        return True, "Reels отправлен в VK!"
    except KeyError as e:
        return False, f"Не найден секрет: {e}."
    except Exception as e:
        return False, f"Ошибка VK: {e}"

# ==================== ИНТЕРФЕЙС ====================
st.set_page_config(page_title="Arsenal Sport Content Manager", layout="wide", page_icon="🏆")

with st.sidebar:
    st.title("Arsenal Sport")
    st.caption("Content Studio · v2.6 MAX")
    dark_mode = st.toggle("🌙 Тёмная тема", value=False, key="theme_toggle")
    st.markdown("---")
    st.markdown(
        '<div class="sidebar-max"><div class="sidebar-max-kicker">ARSENAL SPORT</div>'
        '<div class="sidebar-max-title">⚡ MAX</div>'
        '<div class="sidebar-max-text">Центр управления магазином</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("⚡ Открыть MAX", use_container_width=True, type="primary", key="sidebar_max"):
        st.session_state["open_max"] = True
    st.markdown("---")
    try:
        tg_ch = st.secrets.get("TELEGRAM_CHANNEL", None)
        if tg_ch:
            st.success(f"📡 Telegram: @{tg_ch}")
        else:
            st.info("📡 Telegram не настроен")
    except Exception:
        st.info("📡 Telegram не настроен")
    st.markdown("---")
    st.caption(f"Сегодня · {datetime.date.today().strftime('%d.%m.%Y')}")

if dark_mode:
    bg_css = "body {background:#0b0e13;}"
    theme_css = """
    .stApp {background:#0b0e13!important;color:#f5f7fa!important;}
    section[data-testid="stSidebar"] {background:#10131a!important;border-right:1px solid #252b38!important;}
    div[data-baseweb="tab-list"] {background:#11151d!important;border-color:#252b38!important;}
    [data-testid="stFileUploader"] {background:#11151d!important;border-color:#394152!important;}
    """
else:
    bg_css = "body {background:#eef1f5;}"
    theme_css = """
    .stApp {background:#eef1f5!important;color:#202633!important;}
    section[data-testid="stSidebar"] {background:#e5e9ef!important;border-right:1px solid #d5dbe4!important;}
    div[data-baseweb="tab-list"] {background:#e3e7ed!important;border-color:#d5dbe4!important;}
    [data-testid="stFileUploader"] {background:#f5f7fa!important;border-color:#b9c1ce!important;}
    .sidebar-max {background:linear-gradient(135deg,#f8f9fb,#ece8ff);border-color:#d8d1ff;}
    .sidebar-max-kicker {color:#655bd0;}
    .sidebar-max-title {color:#202633;}
    .sidebar-max-text {color:#687080;}
    """

st.markdown(
    "<style>\n" + bg_css + theme_css + """
:root {--accent:#897dff;--accent2:#6f68d6;--bg:#0b0e13;--surface:#151922;--border:#252b38;--text:#f5f7fa;--muted:#98a0ae;}
.main-title {font-size:2.45rem;font-weight:850;color:#f5f7fa;text-align:center;margin:8px 0 0;letter-spacing:.02em;}
.subtitle {text-align:center;color:#98a0ae;margin:3px 0 18px;font-size:.92rem;}
.stApp {background:#eef1f5;}
section[data-testid="stSidebar"] {background:#e5e9ef;border-right:1px solid #d5dbe4;}
section[data-testid="stSidebar"] .stMetric {background:transparent;border:0;border-radius:0;padding:2px 4px;}
.sidebar-max {padding:10px 12px 8px;border:1px solid #34304f;border-radius:14px;background:linear-gradient(135deg,#171c26,#211f35);margin:2px 0 8px;}
.sidebar-max-kicker {font-size:.62rem;letter-spacing:.12em;font-weight:800;color:#9b93ff;}
.sidebar-max-title {font-size:1.18rem;font-weight:850;color:#fff;margin-top:2px;}
.sidebar-max-text {font-size:.72rem;color:#aeb5c2;margin-top:2px;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
.stButton > button {border-radius:11px;border:1px solid #303747;background:#171c26;color:#f5f7fa;font-weight:650;transition:.2s;}
.stButton > button:hover {border-color:var(--accent);color:#fff;box-shadow:0 0 0 1px rgba(137,125,255,.16);}
button[kind="primary"] {background:linear-gradient(135deg,#756be8,#897dff)!important;border:0!important;color:#fff!important;}
button[kind="primary"]:hover {filter:brightness(1.06);box-shadow:0 6px 22px rgba(137,125,255,.22);}
div[data-baseweb="tab-list"] {gap:6px;background:#e3e7ed;padding:6px;border-radius:14px;border:1px solid #d5dbe4;}
button[data-baseweb="tab"] {border-radius:10px;color:#9da5b3;font-weight:650;}
button[data-baseweb="tab"][aria-selected="true"] {background:#211f35;color:#e8e5ff;}
[data-testid="stFileUploader"] {border:1px dashed #b9c1ce;border-radius:14px;background:#f5f7fa;}
.stat-box {background:linear-gradient(135deg,#171c26 0%,#211f35 100%);border:1px solid #30364a;color:#f5f7fa;padding:20px;border-radius:16px;text-align:center;margin:5px;box-shadow:0 8px 24px rgba(0,0,0,.12);}
.stat-number {font-size:2.35rem;font-weight:900;margin:0;color:#f5f7fa;}
.stat-label {font-size:.9rem;color:#aeb5c2;margin:0;}
.section-kicker {font-size:.76rem;text-transform:uppercase;letter-spacing:.12em;color:#8f86f5;font-weight:800;margin-bottom:4px;}
.section-title {font-size:1.7rem;font-weight:800;margin-bottom:2px;}
.section-subtitle {color:#8f97a6;margin-bottom:18px;}
.pill {display:inline-block;padding:4px 10px;border-radius:999px;background:#211f35;color:#c9c5ff;border:1px solid #34304f;font-size:.78rem;font-weight:650;}
[data-testid="stAlert"], div[data-baseweb="notification"] {background:#151922 !important;border:1px solid #303747 !important;color:#f5f7fa !important;border-radius:14px !important;}
[data-testid="stAlert"] *, div[data-baseweb="notification"] * {color:#f5f7fa !important;}
[data-testid="stAlert"] svg, div[data-baseweb="notification"] svg {color:#897dff !important;}
</style>""",
    unsafe_allow_html=True,
)

st.markdown('<p class="main-title">🏆 ARSENAL SPORT</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Content Manager — управление контентом магазина</p>', unsafe_allow_html=True)
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "📸 Создать", "📦 Каталог", "📱 Тексты", "🎬 Reels",
        "📅 План", "📊 Статистика", "⚙️ Настройки"
    ]
)

# ========== 1: СОЗДАТЬ КАРТОЧКУ ==========
with tab1:
    st.markdown('<div class="section-kicker">CONTENT STUDIO</div><div class="section-title">Создать товар</div><div class="section-subtitle">Загрузите фото, заполните данные и сразу получите готовую карточку.</div>', unsafe_allow_html=True)
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
                card_buf = io.BytesIO()
                card.save(card_buf, format="PNG")
                card_b64 = base64.b64encode(card_buf.getvalue()).decode("ascii")

                original_b64 = None
                if up:
                    original_buf = io.BytesIO()
                    img.save(original_buf, format="JPEG", quality=95)
                    original_b64 = base64.b64encode(original_buf.getvalue()).decode("ascii")

                product_data = {
                    "name": name, "brand": brand, "article": article,
                    "sizes": sizes, "color": color, "description": description,
                    "specs": specs, "category": category,
                    "card_image": card_b64,
                    "date_added": str(datetime.date.today())
                }
                if original_b64:
                    product_data["original_image"] = original_b64

                add_product(product_data)
                st.success("✅ Карточка создана!")
                st.image(card, caption="Готово (1080×1350)", width=400)
                buf = io.BytesIO()
                card.save(buf, format="PNG")
                st.session_state["last_card_bytes"] = buf.getvalue()
                st.session_state["last_card_name"] = name
                st.download_button("⬇️ Скачать карточку", buf.getvalue(),
                    file_name=f"{name.replace(' ','_')}_card.png", mime="image/png")

# ========== 2: КАТАЛОГ ==========
with tab2:
    st.markdown('<div class="section-kicker">PRODUCT LIBRARY</div><div class="section-title">Каталог</div><div class="section-subtitle">Все товары и готовые материалы — в одном рабочем пространстве.</div>', unsafe_allow_html=True)
    st.info("➕ Для нового товара откройте вкладку «📸 Создать».")
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
                    new_original = st.file_uploader(
                        "📷 Исходное фото товара",
                        type=["jpg", "jpeg", "png", "webp"],
                        key=f"orig_{real_i}",
                        help="Фото будет использоваться для автоматического создания карточки и Reels."
                    )
                    if st.button("💾 Сохранить", key=f"save_{real_i}"):
                        updated = {
                            "name": nn, "brand": nb, "article": na, "sizes": ns,
                            "color": nc, "description": nd, "specs": nsp,
                            "category": ncat, "date_added": p.get('date_added', str(datetime.date.today()))
                        }
                        # Не теряем сохранённую карточку и исходное фото.
                        if p.get("card_image"):
                            updated["card_image"] = p["card_image"]
                        if p.get("original_image"):
                            updated["original_image"] = p["original_image"]
                        if new_original:
                            original_buf = io.BytesIO()
                            Image.open(new_original).convert("RGB").save(
                                original_buf, format="JPEG", quality=95
                            )
                            updated["original_image"] = base64.b64encode(
                                original_buf.getvalue()
                            ).decode("ascii")
                        update_product(real_i, updated)
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

        idx = st.selectbox(
            "Товар",
            range(len(names)),
            format_func=lambda x: names[x],
            key="text_product"
        )

        tone = st.radio(
            "Тональность",
            TONES,
            horizontal=True,
            key="text_tone"
        )

        st.caption(f"Выбрано: **{names[idx]}** · Тональность: **{tone}**")

        if st.button(
            "✨ Сгенерировать тексты",
            type="primary",
            use_container_width=True,
            key="generate_texts_btn"
        ):
            p = products[idx]

            # Каждый запуск заново создаёт тексты именно для выбранной тональности.
            st.session_state["tg_text"] = gen_telegram(p, tone)
            st.session_state["insta_text"] = gen_instagram(p, tone)
            st.session_state["vk_text"] = gen_vk(p, tone)
            st.session_state["current_product"] = p
            st.session_state["current_tone"] = tone
            st.session_state["text_generation_id"] = st.session_state.get("text_generation_id", 0) + 1

        if "tg_text" in st.session_state:
            p = st.session_state["current_product"]
            insta = st.session_state["insta_text"]
            tg = st.session_state["tg_text"]
            vk = st.session_state["vk_text"]
            generated_tone = st.session_state.get("current_tone", "")

            st.success(
                f"Тексты созданы: {p.get('brand','')} {p.get('name','')} · «{generated_tone}»"
            )

            st.caption(
                "Показаны тексты для последней нажатой кнопки «Сгенерировать тексты»."
            )

            st.markdown("---")
            st.subheader("📸 Instagram")
            st.text_area(
                "Текст поста",
                insta,
                height=280,
                key=f"i_out_{st.session_state.get('text_generation_id', 0)}"
            )
            st.download_button(
                "⬇️ Скачать текст",
                insta,
                file_name=f"{p.get('name','item')}_insta.txt",
                mime="text/plain",
                key=f"dl_i_{st.session_state.get('text_generation_id', 0)}"
            )
            st.caption("ℹ️ Скопируйте текст и загрузите карточку в Instagram вручную.")

            st.markdown("---")
            st.subheader("✈️ Telegram")
            st.text_area(
                "Текст поста",
                tg,
                height=280,
                key=f"t_out_{st.session_state.get('text_generation_id', 0)}"
            )

            card_to_send = None
            if "last_card_bytes" in st.session_state:
                card_to_send = st.session_state["last_card_bytes"]
            elif p.get("card_image"):
                try:
                    card_to_send = base64.b64decode(p["card_image"])
                except Exception:
                    card_to_send = None

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button(
                    "🚀 Опубликовать в Telegram",
                    type="primary",
                    key=f"pub_tg_text_{st.session_state.get('text_generation_id', 0)}"
                ):
                    if not card_to_send:
                        st.error("Нет карточки. Создайте её во вкладке «📸 Создать» или загрузите файл.")
                    else:
                        ok, msg = publish_to_telegram(card_to_send, tg)
                        (st.success if ok else st.error)(msg)
            with col_b:
                st.download_button(
                    "⬇️ Скачать текст",
                    tg,
                    file_name=f"{p.get('name','item')}_tg.txt",
                    mime="text/plain",
                    key=f"dl_tg_{st.session_state.get('text_generation_id', 0)}"
                )

            st.markdown("---")
            st.subheader("🅥 ВКонтакте")
            st.text_area(
                "Текст поста",
                vk,
                height=200,
                key=f"v_out_{st.session_state.get('text_generation_id', 0)}"
            )
            st.download_button(
                "⬇️ Скачать текст",
                vk,
                file_name=f"{p.get('name','item')}_vk.txt",
                mime="text/plain",
                key=f"dl_vk_{st.session_state.get('text_generation_id', 0)}"
            )

# ========== 4: REELS & STORIES ==========
with tab4:
    st.markdown('<div class="section-kicker">SHORT VIDEO</div><div class="section-title">Reels & Stories</div><div class="section-subtitle">Идея → сценарий → видео → публикация.</div>', unsafe_allow_html=True)
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

        st.markdown("---")

        st.subheader("🎞️ Видео-рилс из карточки")

        # По умолчанию Reels использует готовую карточку выбранного товара.
        reel_product = products[st.session_state.get("r_sel", 0)]
        stored_card = reel_product.get("card_image")

        # Совместимость со старыми товарами.
        if not stored_card and st.session_state.get("last_card_name") == reel_product.get("name"):
            stored_card = base64.b64encode(
                st.session_state.get("last_card_bytes", b"")
            ).decode("ascii")

        replace_reel_photo = st.checkbox(
            "🔄 Заменить фото для этого Reels",
            value=False,
            key="replace_reel_photo"
        )

        reel_file = None
        if replace_reel_photo:
            reel_file = st.file_uploader(
                "Выберите другое изображение",
                type=["jpg", "jpeg", "png", "webp"],
                key="reel_card_replace"
            )

        if stored_card and not replace_reel_photo:
            st.info(
                f"📎 Используется карточка товара: "
                f"**{reel_product.get('brand','')} {reel_product.get('name','')}**"
            )
        elif not stored_card and not replace_reel_photo:
            st.info(
                "ℹ️ У этого товара нет сохранённой карточки. "
                "При создании Reels карточка будет создана автоматически "
                "из данных товара и сохранена в каталоге."
            )

        if st.button("🎬 Создать видео", key="make_reel_btn"):
            import tempfile, os
            from reels import make_reel

            if replace_reel_photo:
                if not reel_file:
                    st.error("Выбери изображение для замены.")
                    st.stop()
                source_bytes = reel_file.getvalue()
            else:
                if not stored_card:
                    # Используем исходное фото, если оно сохранено у товара.
                    source_image = None
                    original_b64 = reel_product.get("original_image")
                    if original_b64:
                        try:
                            source_image = Image.open(
                                io.BytesIO(base64.b64decode(original_b64))
                            ).convert("RGB")
                        except Exception:
                            source_image = None

                    if source_image is None:
                        st.error(
                            "❌ Нельзя создать Reels: у товара нет исходного фото. "
                            "Открой «📦 Каталог → ✏️ Редактировать», загрузи фото товара и сохрани."
                        )
                        st.stop()

                    auto_card = generate_card(
                        source_image,
                        reel_product.get("name", ""),
                        reel_product.get("brand", ""),
                        reel_product.get("article", ""),
                        reel_product.get("sizes", ""),
                        reel_product.get("color", ""),
                        reel_product.get("description", ""),
                        reel_product.get("specs", ""),
                        reel_product.get("category", "Другое"),
                        "Спортивный",
                    )
                    card_buf = io.BytesIO()
                    auto_card.save(card_buf, format="PNG")
                    source_bytes = card_buf.getvalue()

                    # Сохраняем автоматически созданную карточку в каталоге.
                    updated_product = dict(reel_product)
                    updated_product["card_image"] = base64.b64encode(source_bytes).decode("ascii")
                    update_product(st.session_state.get("r_sel", 0), updated_product)
                    reel_product = updated_product
                    stored_card = updated_product["card_image"]

                    st.success(
                        "✅ Карточка автоматически создана с исходным фото товара и сохранена."
                    )
                else:
                    source_bytes = base64.b64decode(stored_card)

            with tempfile.TemporaryDirectory() as tmp:
                src = os.path.join(tmp, "card.png")
                with open(src, "wb") as f:
                    f.write(source_bytes)

                out = os.path.join(tmp, "reel.mp4")
                with st.spinner("Рендерю видео, подожди..."):
                    make_reel(src, out, duration=8)

                with open(out, "rb") as f:
                    video_bytes = f.read()

            st.video(video_bytes)

            st.download_button(
                "⬇️ Скачать рилс",
                video_bytes,
                "reel.mp4",
                "video/mp4",
                key="dl_reel"
            )

            st.markdown("### 📤 Опубликовать Reels")
            reel_caption = gen_instagram(reel_product, "Продающий")

            pub1, pub2, pub3 = st.columns(3)

            with pub1:
                if st.button("✈️ В Telegram", key="publish_reel_tg"):
                    with st.spinner("Отправляю Reels в Telegram..."):
                        ok, msg = publish_reel_to_telegram(video_bytes, reel_caption)
                    (st.success if ok else st.error)(msg)

            with pub2:
                if st.button("🅥 В VK", key="publish_reel_vk"):
                    with st.spinner("Отправляю Reels в VK..."):
                        ok, msg = publish_reel_to_vk(video_bytes, reel_caption)
                    (st.success if ok else st.error)(msg)

            with pub3:
                st.button(
                    "📸 В Instagram",
                    key="publish_reel_instagram",
                    disabled=True,
                    help="Для автоматической публикации Instagram требует публичный URL видео и подключение Meta API."
                )

            st.caption(
                "Telegram и VK публикуются непосредственно из приложения. "
                "Instagram подключим после добавления публичного хранилища для MP4 и Meta API."
            )

        st.markdown("---")


# ========== 5: КОНТЕНТ-ПЛАН ==========
with tab5:
    st.markdown('<div class="section-kicker">CONTENT PLANNER</div><div class="section-title">Контент-план</div><div class="section-subtitle">Планируйте публикации по датам, платформам и статусам.</div>', unsafe_allow_html=True)
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
                        pr_icon = {"Обычный":"○","Высокий":"◐","Срочно":"●"}.get(item.get('priority','Обычный'),'○')
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
    st.markdown('<div class="section-kicker">ANALYTICS</div><div class="section-title">Статистика</div><div class="section-subtitle">Ключевые показатели контентной работы.</div>', unsafe_allow_html=True)
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

def ai_sales_reply(products, message):
    q = (message or "").strip()
    if not q:
        return "Напишите, что ищете — например: «бутсы 42 размера до 10000».", []
    found = product_search(products, q)
    lower = q.lower()
    if any(k in lower for k in ("достав", "оплат", "возврат", "налич", "размер")) and not found:
        return knowledge_answer(q), []
    if found:
        top = found[:5]
        lines = ["Нашёл подходящие варианты:"]
        for i, p in enumerate(top, 1):
            title = f"{p.get('brand','')} {p.get('name','')}".strip()
            details = []
            if p.get("sizes"): details.append(f"размеры: {p.get('sizes')}")
            if p.get("color"): details.append(f"цвет: {p.get('color')}")
            if p.get("article"): details.append(f"арт.: {p.get('article')}")
            lines.append(f"{i}. {title}" + (f" — {', '.join(details)}" if details else ""))
        lines.append("Выберите номер товара — помогу с деталями и следующим шагом.")
        return "\n".join(lines), top
    return "Пока не нашёл точного совпадения. Напишите категорию, размер, цвет или бюджет — попробую подобрать из каталога.", []

def sales_followup(products, message, current):
    q = (message or "").strip().lower()
    if not q:
        return "Напишите, что хотите уточнить.", current
    if current:
        nums = [int(x) for x in re.findall(r"\b([1-5])\b", q)]
        if nums:
            idx = nums[0] - 1
            if idx < len(current):
                p = current[idx]
                title = f"{p.get('brand','')} {p.get('name','')}".strip()
                return (f"{title}. {p.get('description','Описание пока не заполнено.') or 'Описание пока не заполнено.'} "
                        f"Размеры: {p.get('sizes','уточняйте')}. Цвет: {p.get('color','уточняйте')}. "
                        f"Артикул: {p.get('article','уточняйте')}. Наличие подтверждается перед заказом."), [p]
    if any(k in q for k in ("достав", "оплат", "возврат", "налич", "размер")):
        return knowledge_answer(q), current
    found = product_search(products, q)
    if found:
        return ai_sales_reply(products, message)[0], found
    return "Уточните размер, бюджет, цвет или вид товара — я попробую подобрать подходящий вариант.", current


# ==================== MAX SMART FUNCTIONS ====================
ORDER_STATUSES = ["Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен", "Завершён", "Отменён"]
ACTIVE_ORDER_STATUSES = {"Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен"}

def max_stock(product):
    by_size = product.get("stock_by_size") or {}
    if isinstance(by_size, dict):
        try:
            return sum(max(0, int(v or 0)) for v in by_size.values())
        except Exception:
            return 0
    try:
        return max(0, int(product.get("total_stock", 0) or 0))
    except Exception:
        return 0

def max_product_title(product):
    return f"{product.get('brand','')} {product.get('name','')}".strip() or "Товар"

def max_due_content(plan):
    today = datetime.date.today()
    due, overdue = [], []
    for item in plan:
        try:
            d = datetime.date.fromisoformat(str(item.get("date","")))
        except Exception:
            continue
        if item.get("status") == "Опубликовано":
            continue
        if d < today: overdue.append(item)
        elif d == today: due.append(item)
    return due, overdue

def max_store_metrics(products, leads, orders, plan):
    active = [o for o in orders if o.get("status","Новая") in ACTIVE_ORDER_STATUSES]
    completed = [o for o in orders if o.get("status") == "Завершён"]
    total_amount = 0.0
    for o in orders:
        for key in ("total","amount","sum","total_amount","price"):
            try:
                if o.get(key) not in (None, ""):
                    total_amount += float(str(o.get(key)).replace(" ","").replace(",","."))
                    break
            except Exception:
                pass
    lead_to_order = sum(x.get("status") == "Заказ оформлен" for x in leads)
    conversion = (lead_to_order / len(leads) * 100) if leads else 0
    category_counts = {}
    for p in products:
        cat = p.get("category","Другое")
        category_counts[cat] = category_counts.get(cat,0) + 1
    return {"active_orders":len(active),"completed_orders":len(completed),"amount":total_amount,
            "conversion":conversion,"categories":sorted(category_counts.items(), key=lambda x:(-x[1],x[0])),
            "published":sum(1 for x in plan if x.get("status")=="Опубликовано"),"content_total":len(plan)}

def max_advanced_search(products, query, category="Все", brand="Все", size="Все", color="Все"):
    q=(query or "").strip().lower(); result=[]
    for p in products:
        if category!="Все" and p.get("category","Другое")!=category: continue
        if brand!="Все" and p.get("brand","")!=brand: continue
        if size!="Все" and size.lower() not in str(p.get("sizes","")).lower(): continue
        if color!="Все" and color.lower() not in str(p.get("color","")).lower(): continue
        hay=" ".join(str(p.get(k,"")) for k in ("name","brand","article","category","description","specs","sizes","color")).lower()
        if q and q not in hay: continue
        result.append(p)
    return result

def max_ideas(products, count=10):
    ideas=[("Польза","Показать, какую задачу спортсмена решает товар."),
           ("Сравнение","Сравнить товар с другим вариантом из каталога по назначению."),
           ("Детали","Крупные планы материала, подошвы, посадки или конструкции."),
           ("Подбор","Мини-гид: как выбрать этот тип товара под задачу клиента."),
           ("FAQ","Ответить на частый вопрос покупателя о размере, использовании или уходе."),
           ("Тест","Показать товар в реальном спортивном сценарии."),
           ("Образ","Собрать комплект вокруг товара из ассортимента Arsenal Sport."),
           ("История","Короткая история бренда или технологии без перегрузки рекламой."),
           ("Отзывы","Формат для реальных отзывов и впечатлений покупателей."),
           ("Новинка","Показать поступление: что изменилось и кому подходит.")]
    if not products: return [{"title":x[0],"product":"Каталог пуст","idea":x[1]} for x in ideas[:count]]
    return [{"title":ideas[i%len(ideas)][0],"product":max_product_title(products[i%len(products)]),"idea":ideas[i%len(ideas)][1]} for i in range(count)]

def max_sales_reply(products, state, message):
    text=(message or "").strip(); q=text.lower(); state=dict(state or {}); state["last_message"]=text
    if any(x in q for x in ("стоп","отмена","сброс")): return "Диалог сброшен. Напишите, что ищете.", {}, []
    m=re.search(r"(?<!\d)(\d{2})(?:\s*(?:размер|р\.?))?(?!\d)",q)
    if m: state["size"]=m.group(1)
    m=re.search(r"(?:до|бюджет|не дороже)\s*(\d[\d\s]*)",q)
    if m: state["budget"]=m.group(1).replace(" ","")
    for key,words in {"surface":["искусствен","зал","асфальт","стадион","грунт","улиц"],"purpose":["футбол","баскетбол","бег","трениров","теннис","волейбол"],"color":["черн","бел","син","красн","зелен","сер"]}.items():
        for w in words:
            if w in q: state[key]=w; break
    missing=[]
    if "purpose" not in state: missing.append("purpose")
    elif "size" not in state: missing.append("size")
    elif "surface" not in state and state.get("purpose") in ("футбол","бег","теннис"): missing.append("surface")
    if missing:
        prompts={"purpose":"Что ищете: футбол, бег, баскетбол, теннис, тренировки или другой вид спорта?",
                 "size":"Какой нужен размер?","surface":"Где будете использовать: зал, искусственное поле, улица, стадион или другое покрытие?"}
        return prompts[missing[0]],state,[]
    query=" ".join(str(state.get(k,"")) for k in ("purpose","surface","size","color"))
    found=product_search(products,query) or product_search(products,state.get("purpose",""))
    if not found: return "Подходящий товар по этим параметрам не найден. Можно расширить поиск или передать запрос менеджеру.",state,[]
    return f"Нашёл {min(3,len(found))} вариант(а). Показываю наиболее подходящие. Актуальное наличие подтвердит менеджер.",state,found[:3]

# ========== MAX: ВСПЛЫВАЮЩЕЕ ОКНО ==========

@st.dialog("⚡ ARSENAL SPORT MAX", width="large")
def max_dialog():
    st.markdown('<div class="section-kicker">MANAGER WORKSPACE</div><div class="section-title">Рабочее место менеджера</div><div class="section-subtitle">Единая панель продаж: обращения, заказы и остатки — без изменения структуры Arsenal Sport.</div>', unsafe_allow_html=True)

    manager_leads = load_leads()
    manager_orders = load_json(Path("orders.json"), [])
    manager_products = load_products()
    manager_plan = load_plan()

    # ---------- 1. Умный помощник менеджера ----------
    due_today, overdue = max_due_content(manager_plan)
    incomplete_cards = [p for p in manager_products if not p.get("description") or not (p.get("card_image") or p.get("original_image"))]
    out_of_stock = [p for p in manager_products if max_stock(p) == 0]
    assistant_tasks = []
    if new_leads_count: assistant_tasks.append(("🔥","Обработать новые обращения",f"{new_leads_count} новых"))
    if low_stock_products: assistant_tasks.append(("📦","Проверить остатки",f"{len(low_stock_products)} позиций"))
    if out_of_stock: assistant_tasks.append(("⛔","Проверить товары без остатка",f"{len(out_of_stock)} позиций"))
    if incomplete_cards: assistant_tasks.append(("📸","Доработать карточки",f"{len(incomplete_cards)} товаров"))
    if due_today: assistant_tasks.append(("📅","Опубликовать контент сегодня",f"{len(due_today)} задач"))
    if overdue: assistant_tasks.append(("⚠️","Закрыть просроченный контент",f"{len(overdue)} задач"))
    st.markdown("### 🧠 Что сегодня нужно сделать")
    if assistant_tasks:
        for icon,title,count in assistant_tasks:
            st.warning(f"{icon} **{title}** — {count}")
    else:
        st.success("Основные задачи на сегодня не найдены.")
    with st.expander("Показать детали задач"):
        if incomplete_cards: st.write("**Карточки без полного контента:**", ", ".join(max_product_title(p) for p in incomplete_cards[:20]))
        if due_today: st.write("**Контент сегодня:**", ", ".join(str(x.get("product","")) for x in due_today))
        if overdue: st.write("**Просрочено:**", ", ".join(str(x.get("product","")) for x in overdue))
        if out_of_stock: st.write("**Нет в наличии:**", ", ".join(max_product_title(p) for p in out_of_stock[:20]))

    # ---------- 2. Центр продаж ----------
    store_stats = max_store_metrics(manager_products, manager_leads, manager_orders, manager_plan)
    st.markdown("### 🔥 Центр продаж")
    s1,s2,s3,s4,s5 = st.columns(5)
    s1.metric("Новые лиды", new_leads_count)
    s2.metric("В работе", in_work_count)
    s3.metric("Активные заказы", store_stats["active_orders"])
    s4.metric("Завершено", store_stats["completed_orders"])
    s5.metric("Конверсия", f"{store_stats['conversion']:.1f}%")
    if store_stats["amount"]:
        st.caption(f"Сумма заказов с распознанной суммой: {store_stats['amount']:,.0f} ₽".replace(",", " "))
    if store_stats["categories"]:
        st.caption("Категории каталога: " + " · ".join(f"{k}: {v}" for k,v in store_stats["categories"]))

    with st.expander("📊 Аналитика магазина"):
        a1,a2,a3=st.columns(3)
        a1.metric("Контента создано", store_stats["content_total"])
        a2.metric("Опубликовано", store_stats["published"])
        a3.metric("Всего обращений", len(manager_leads))
        st.write("Популярность категорий в каталоге")
        for cat,count in store_stats["categories"][:10]:
            st.progress(min(1.0,count/max(1,len(manager_products))), text=f"{cat} · {count}")

    # ---------- 3. Полный контроль склада ----------
    with st.expander("📦 Умный склад", expanded=False):
        w1,w2,w3,w4=st.columns(4)
        low_sizes=sum(1 for p in manager_products if isinstance(p.get("stock_by_size"),dict) and any(int(v or 0)<=1 for v in p.get("stock_by_size",{}).values()))
        no_photos=sum(1 for p in manager_products if not (p.get("card_image") or p.get("original_image")))
        no_desc=sum(1 for p in manager_products if not p.get("description"))
        w1.metric("Мало товара",len(low_stock_products)); w2.metric("Нет товара",len(out_of_stock)); w3.metric("Мало размеров",low_sizes); w4.metric("Без контента",no_photos+no_desc)
        stock_filter=st.selectbox("Показать",["Все проблемные","Мало","Нет","Без фото","Без описания"],key="max_stock_filter")
        problem=[]
        for p in manager_products:
            stck=max_stock(p)
            bad=(stock_filter=="Все проблемные" and (stck<=3 or not p.get("description") or not (p.get("card_image") or p.get("original_image")))) or (stock_filter=="Мало" and 0<stck<=3) or (stock_filter=="Нет" and stck==0) or (stock_filter=="Без фото" and not (p.get("card_image") or p.get("original_image"))) or (stock_filter=="Без описания" and not p.get("description"))
            if bad: problem.append(p)
        for p in problem[:20]:
            st.write(f"• **{max_product_title(p)}** · остаток: {max_stock(p)} · фото: {'да' if (p.get('card_image') or p.get('original_image')) else 'нет'} · описание: {'да' if p.get('description') else 'нет'}")
        if len(problem)>20: st.caption(f"Показаны первые 20 из {len(problem)}.")

    # ---------- 4. Расширенный поиск ----------
    with st.expander("🔎 Расширенный поиск", expanded=False):
        brands=sorted({str(p.get("brand","")) for p in manager_products if p.get("brand")})
        sizes=sorted({str(p.get("sizes","")) for p in manager_products if p.get("sizes")})
        colors=sorted({str(p.get("color","")) for p in manager_products if p.get("color")})
        ec1,ec2=st.columns(2)
        search_q=ec1.text_input("Название / артикул / описание / характеристики",key="max_adv_q")
        category=ec2.selectbox("Категория",["Все"]+CATEGORIES,key="max_adv_cat")
        ec3,ec4=st.columns(2)
        brand=ec3.selectbox("Бренд",["Все"]+brands,key="max_adv_brand")
        color=ec4.selectbox("Цвет",["Все"]+colors,key="max_adv_color")
        size=st.text_input("Размер",key="max_adv_size",placeholder="Например: 42")
        adv_found=max_advanced_search(manager_products,search_q,category,brand,size or "Все",color)
        st.caption(f"Найдено: {len(adv_found)}")
        for p in adv_found[:15]: st.write(f"• **{max_product_title(p)}** · {p.get('category','Другое')} · {p.get('sizes','уточняйте')}")

    # ---------- 5. Генератор идей + автоплан ----------
    with st.expander("💡 Генератор идей", expanded=False):
        idea_count=st.slider("Количество идей",3,15,10,key="max_idea_count")
        if st.button("✨ Сгенерировать идеи",key="max_ideas_btn"):
            st.session_state["max_ideas"]=max_ideas(manager_products,idea_count)
        for idea in st.session_state.get("max_ideas",[]):
            st.write(f"**{idea['title']} · {idea['product']}** — {idea['idea']}")
        if st.button("📅 Добавить идеи в план",key="max_ideas_plan"):
            for i,idea in enumerate(st.session_state.get("max_ideas",[])):
                add_plan({"date":str(datetime.date.today()+datetime.timedelta(days=i)),"platform":"Instagram","product":idea["product"],"type":"Reels" if i%3==0 else "Пост","idea":idea["idea"],"status":"Идея","priority":"Обычный"})
            st.success("Идеи добавлены в контент-план.")
            st.rerun()

    # ---------- 6. Контент-автомат ----------
    with st.expander("🎯 Контент-автомат «Сделать всё»", expanded=False):
        if manager_products:
            auto_names=[max_product_title(p) for p in manager_products]
            ai=st.selectbox("Товар",range(len(auto_names)),format_func=lambda x:auto_names[x],key="max_auto_product")
            if st.button("⚡ Сделать всё для товара",type="primary",key="max_make_all"):
                p=manager_products[ai]
                st.session_state["max_auto_bundle"]=auto_content_bundle(p)
                st.session_state["max_auto_product_title"]=max_product_title(p)
                st.session_state["max_auto_plan_item"]={"date":str(datetime.date.today()),"platform":"Instagram","product":max_product_title(p),"type":"Reels","idea":f"Reels + пост + Stories для {max_product_title(p)}","status":"Идея","priority":"Высокий"}
            if "max_auto_bundle" in st.session_state:
                st.success(f"Готов контент-пакет: {st.session_state.get('max_auto_product_title','')}")
                ab=st.session_state["max_auto_bundle"]
                for label,key in [("Instagram","instagram"),("Telegram","telegram"),("VK","vk"),("Reels","reels_hook"),("Stories","stories")]:
                    st.text_area(label,ab[key],height=100,key=f"auto_{key}")
                if st.button("📅 Добавить в план",key="max_auto_add_plan"):
                    add_plan(st.session_state["max_auto_plan_item"]); st.success("Добавлено в план."); st.rerun()
                st.caption("Дальше менеджер может отредактировать тексты и опубликовать их через существующие инструменты.")

    # ---------- 7. AI-продавец 2.0 ----------
    st.markdown("### 🤖 AI-продавец 2.0")
    st.caption("Квалифицирует запрос по виду спорта, размеру и сценарию использования, затем ищет товар и передаёт клиента менеджеру.")
    if "seller2_state" not in st.session_state: st.session_state["seller2_state"]={}
    with st.form("seller2_form",clear_on_submit=True):
        seller2_msg=st.text_input("Сообщение покупателя",placeholder="Ищу бутсы для искусственного поля, 42 размер")
        seller2_send=st.form_submit_button("💬 Продолжить диалог",type="primary")
    if seller2_send and seller2_msg:
        reply,new_state,seller2_found=max_sales_reply(manager_products,st.session_state.get("seller2_state",{}),seller2_msg)
        st.session_state["seller2_state"]=new_state
        st.session_state["seller2_found"]=seller2_found
        st.session_state.setdefault("seller2_chat",[]).extend([("Покупатель",seller2_msg),("Arsenal Sport",reply)])
    for role,msg in st.session_state.get("seller2_chat",[])[-8:]:
        st.caption(role); st.write(msg)
    seller2_found=st.session_state.get("seller2_found",[])
    if seller2_found:
        st.markdown("**Подходящие варианты**")
        for i,p in enumerate(seller2_found):
            st.write(f"{i+1}. **{max_product_title(p)}** · {p.get('sizes','уточняйте')} · {p.get('color','уточняйте')}")
        if st.button("📥 Передать квалифицированного клиента в CRM",key="seller2_crm",type="primary"):
            if seller2_found:
                lead=create_lead("Клиент","не указан","AI-продавец 2.0",st.session_state.get("seller2_state",{}).get("last_message",""),max_product_title(seller2_found[0]))
                st.success(f"Обращение #{lead.get('id')} создано. Менеджеру останется уточнить контакт и наличие.")



    def _manager_stock(product):
        by_size = product.get("stock_by_size") or {}
        if isinstance(by_size, dict):
            return sum(max(0, int(v or 0)) for v in by_size.values())
        try:
            return max(0, int(product.get("total_stock", 0) or 0))
        except Exception:
            return 0

    new_leads_count = sum(1 for x in manager_leads if x.get("status") == "Новый")
    in_work_count = sum(1 for x in manager_leads if x.get("status") == "В работе")
    active_order_statuses = {"Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен"}
    active_orders_count = sum(1 for x in manager_orders if x.get("status", "Новая") in active_order_statuses)
    low_stock_products = [p for p in manager_products if 0 < _manager_stock(p) <= 3]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Новые обращения", new_leads_count)
    k2.metric("В работе", in_work_count)
    k3.metric("Активные заказы", active_orders_count)
    k4.metric("Мало товара", len(low_stock_products))

    d1, d2 = st.columns(2)
    with d1:
        st.markdown("#### Последние обращения")
        if manager_leads:
            for lead in reversed(manager_leads[-5:]):
                st.write(f"**#{lead.get('id', '—')} · {lead.get('name', 'Клиент')}** · {lead.get('status', 'Новый')}")
                st.caption(f"{lead.get('contact', '—')} · {lead.get('product', 'Товар не указан')}")
                current_lead_status = lead.get("status", "Новый")
                new_lead_status = st.selectbox(
                    "Статус",
                    CRM_STATUSES,
                    index=CRM_STATUSES.index(current_lead_status) if current_lead_status in CRM_STATUSES else 0,
                    key=f"manager_lead_status_{lead.get('id')}",
                )
                if new_lead_status != current_lead_status:
                    update_lead(lead.get("id"), status=new_lead_status)
                    st.rerun()
        else:
            st.info("Новых обращений пока нет.")

    with d2:
        st.markdown("#### Последние заказы")
        if manager_orders:
            for order in reversed(manager_orders[-5:]):
                customer = order.get("customer_name", "Клиент")
                status = order.get("status", "Новая")
                order_id = order.get("id", "—")
                st.write(f"**{order_id} · {customer}** · {status}")
                st.caption(f"Контакт: {order.get('customer_contact', '—')}")
                if order.get("lead_id"):
                    st.caption(f"CRM: обращение #{order.get('lead_id')}")
                new_order_status = st.selectbox(
                    "Статус заказа",
                    ["Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен", "Завершён", "Отменён"],
                    index=["Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен", "Завершён", "Отменён"].index(status) if status in ["Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен", "Завершён", "Отменён"] else 0,
                    key=f"manager_order_status_{order_id}",
                )
                if new_order_status != status:
                    order["status"] = new_order_status
                    save_json(Path("orders.json"), manager_orders)
                    if order.get("lead_id"):
                        if new_order_status == "Завершён":
                            update_lead(order["lead_id"], status="Завершён")
                        elif new_order_status == "Отменён":
                            update_lead(order["lead_id"], status="Отменён")
                        elif new_order_status != "Новая":
                            update_lead(order["lead_id"], status="Заказ оформлен")
                    st.rerun()
        else:
            st.info("Заказов пока нет.")

    if low_stock_products:
        st.markdown("#### Контроль остатков")
        for product in sorted(low_stock_products, key=_manager_stock):
            title = f"{product.get('brand', '')} {product.get('name', '')}".strip()
            st.warning(f"{title or 'Товар'} — осталось {_manager_stock(product)} шт.")

    st.markdown("---")
    st.markdown('<div class="section-kicker">ARSENAL SPORT MAX</div><div class="section-title">Центр управления</div><div class="section-subtitle">Бесплатное ядро: каталог, умный поиск, контент-пакет, база знаний и автоплан.</div>', unsafe_allow_html=True)

    products_max = load_products()
    plan_max = load_plan()
    metrics = catalog_metrics(products_max, plan_max)

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Товаров", metrics["products"])
    m2.metric("Карточек", metrics["cards"])
    m3.metric("Фото", metrics["original_photos"])
    m4.metric("В плане", metrics["planned"])
    m5.metric("Опубликовано", metrics["published"])

    st.markdown("---")
    st.subheader("🔎 Умный поиск по каталогу")
    q = st.text_input("Запрос", placeholder="Например: чёрные кроссовки для футбола")
    found = product_search(products_max, q)
    if q:
        st.caption(f"Найдено: {len(found)}")
    for p in found[:8]:
        st.write(f"**{p.get('brand','')} {p.get('name','')}** · {p.get('category','Другое')} · размеры: {p.get('sizes','уточняйте')}")

    if products_max:
        st.markdown("---")
        st.subheader("⚡ Контент-пакет за один шаг")
        bundle_names = [f"{p.get('brand','')} {p.get('name','')}".strip() for p in products_max]
        bi = st.selectbox("Товар для пакета", range(len(bundle_names)), format_func=lambda x: bundle_names[x], key="max_bundle_product")
        if st.button("🚀 Собрать Instagram + Telegram + VK + Reels + Stories", type="primary"):
            bundle = auto_content_bundle(products_max[bi])
            st.session_state["max_bundle"] = bundle
        if "max_bundle" in st.session_state:
            b = st.session_state["max_bundle"]
            st.text_area("Instagram", b["instagram"], height=170, key="max_i")
            st.text_area("Telegram", b["telegram"], height=150, key="max_t")
            st.text_area("VK", b["vk"], height=140, key="max_v")
            st.text_area("Reels — хук", b["reels_hook"], height=90, key="max_r")
            st.text_area("Stories", b["stories"], height=120, key="max_s")

        st.markdown("---")
        st.subheader("📅 Автоплан на 7 дней")
        if st.button("Создать 7 идей из каталога", key="max_plan_btn"):
            suggestions = planner_suggestions(products_max)
            for item in suggestions:
                add_plan(item)
            st.success(f"Добавлено {len(suggestions)} идей в контент-план.")
            st.rerun()

    st.markdown("---")
    st.subheader("🤖 Бесплатный AI-продавец — живой диалог")
    st.caption("Пишите обычным языком. Продавец ищет товары в каталоге и ведёт диалог без платного AI API.")
    if "sales_chat" not in st.session_state:
        st.session_state["sales_chat"] = []
    with st.form("sales_chat_form", clear_on_submit=True):
        customer_msg = st.text_input("Сообщение покупателя", placeholder="Нужны бутсы для искусственного поля, 42 размер, до 10000")
        send = st.form_submit_button("💬 Ответить", type="primary")
    if send and customer_msg:
        current = st.session_state.get("sales_last_found", [])
        reply, chat_found = sales_followup(products_max, customer_msg, current)
        st.session_state["sales_chat"].append(("Покупатель", customer_msg))
        st.session_state["sales_chat"].append(("Arsenal Sport", reply))
        st.session_state["sales_last_found"] = chat_found
    for role, msg in st.session_state["sales_chat"][-10:]:
        st.markdown(f"**{role}:**")
        st.info(msg) if role == "Arsenal Sport" else st.write(msg)
    last_found = st.session_state.get("sales_last_found", [])
    if last_found:
        st.markdown("**Карточки найденных товаров**")
        st.markdown("### 🧾 Передать обращение в CRM")
        st.caption("Если клиент готов продолжить, обращение сохраняется в CRM. Это не подтверждает наличие или оплату товара.")
        lead_name = st.text_input("Имя клиента", key="sales_lead_name")
        lead_contact = st.text_input("Телефон / Telegram", key="sales_lead_contact")
        lead_message = st.text_area("Комментарий клиента", value=st.session_state.get("sales_chat", [])[-1][1] if st.session_state.get("sales_chat") else "", key="sales_lead_message")
        lead_product = f"{last_found[0].get('brand','')} {last_found[0].get('name','')}".strip()
        if st.button("📥 Создать обращение в CRM", type="primary", key="create_sales_lead"):
            if not lead_contact.strip():
                st.error("Укажите телефон или Telegram клиента.")
            else:
                lead = create_lead(
                    lead_name.strip() or "Клиент",
                    lead_contact.strip(),
                    "AI-продавец",
                    lead_message.strip(),
                    lead_product,
                )
                st.success(f"Обращение {lead.get('id', '—')} сохранено в CRM.")
                st.rerun()
        for idx, p in enumerate(last_found):
            title = f"{p.get('brand','')} {p.get('name','')}".strip()
            st.markdown(f"### {idx+1}. {title}")
            cols = st.columns(4)
            with cols[0]:
                img = p.get("card_image") or p.get("original_image")
                if img:
                    try:
                        st.image(img, use_container_width=True)
                    except Exception:
                        st.caption("Фото товара доступно в карточке каталога.")
                else:
                    st.caption("Фото пока не добавлено.")
            with cols[1]:
                st.write(f"**Категория:** {p.get('category','Другое')}")
                st.write(f"**Размеры:** {p.get('sizes','уточняйте')}")
                st.write(f"**Цвет:** {p.get('color','уточняйте')}")
                st.write(f"**Артикул:** {p.get('article','уточняйте')}")
            with cols[2]:
                st.write(p.get("description","Описание пока не заполнено.") or "Описание пока не заполнено.")
            with cols[3]:
                if st.button("🔎 Подробнее", key=f"sales_details_{idx}"):
                    st.session_state[f"sales_detail_{idx}"] = not st.session_state.get(f"sales_detail_{idx}", False)
                if st.button("📦 Наличие", key=f"sales_stock_{idx}"):
                    st.session_state["sales_stock_message"] = f"По товару «{title}» актуальное наличие нужно подтвердить перед заказом."
                if st.button("🛒 Заказать", key=f"sales_order_{idx}"):
                    st.session_state["sales_order_message"] = f"Заказ по товару «{title}»: напишите менеджеру Arsenal Sport и укажите товар, размер и количество."
            if st.session_state.get(f"sales_detail_{idx}"):
                st.info(f"{p.get('description','Описание пока не заполнено.') or 'Описание пока не заполнено.'}\n\nХарактеристики: {p.get('specs','уточняются')}")
        if st.session_state.get("sales_stock_message"):
            st.warning(st.session_state["sales_stock_message"])
        if st.session_state.get("sales_order_message"):
            st.success(st.session_state["sales_order_message"])
    if st.session_state["sales_chat"] and st.button("🗑️ Очистить диалог", key="clear_sales_chat"):
        st.session_state["sales_chat"] = []
        st.session_state["sales_last_found"] = []
        st.rerun()
    st.markdown("### 👤 Полный CRM")
    crm_leads = load_leads()
    if crm_leads:
        crm_pick = st.selectbox("Карточка клиента", list(range(len(crm_leads))), format_func=lambda i: f"#{crm_leads[i].get('id')} · {crm_leads[i].get('name','Клиент')} · {crm_leads[i].get('contact','—')}", key="max_customer_pick")
        customer = crm_leads[crm_pick]
        cc1,cc2=st.columns(2)
        with cc1:
            st.write(f"**Статус:** {customer.get('status','Новый')}")
            st.write(f"**Источник:** {customer.get('source','—')}")
            st.write(f"**Товар:** {customer.get('product','—')}")
            st.write(f"**Создано:** {customer.get('created_at','—')}")
            notes=st.text_area("Заметки менеджера",value=customer.get("notes",""),key=f"cust_notes_{customer.get('id')}")
            customer_status=st.selectbox("Статус клиента",["Новый","Потенциальный","Постоянный"],index=["Новый","Потенциальный","Постоянный"].index(customer.get("customer_status","Новый")) if customer.get("customer_status","Новый") in ["Новый","Потенциальный","Постоянный"] else 0,key=f"cust_type_{customer.get('id')}")
            if st.button("💾 Сохранить карточку",key=f"save_customer_{customer.get('id')}"):
                set_customer_profile(customer.get("id"),notes,customer.get("interested_products") or [customer.get("product","")],customer_status)
                st.success("Карточка клиента сохранена.")
                st.rerun()
        with cc2:
            st.markdown("**История взаимодействий**")
            history=customer.get("history",[])
            if history:
                for h in reversed(history[-10:]): st.caption(f"{h.get('time','')} · {h.get('direction','')}"); st.write(h.get("message",""))
            else: st.info("История появится после добавления взаимодействий.")
            interaction=st.text_area("Добавить взаимодействие",key=f"interaction_{customer.get('id')}")
            if st.button("➕ Записать",key=f"add_interaction_{customer.get('id')}"):
                if interaction.strip(): add_lead_interaction(customer.get("id"),interaction.strip()); st.success("Взаимодействие записано."); st.rerun()
    else:
        st.info("CRM пока пуст.")
    
    st.markdown("### 📊 CRM")

    st.caption("Воронка AI-продавца: новое обращение → работа менеджера → заказ → завершение.")
    crm_leads = load_leads()
    if crm_leads:
        lead_status = st.selectbox("Фильтр обращений", ["Все"] + CRM_STATUSES, key="crm_lead_filter")
        visible_leads = crm_leads if lead_status == "Все" else [x for x in crm_leads if x.get("status") == lead_status]
        for lead in reversed(visible_leads[-30:]):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2.5, 3, 2])
                c1.markdown(f"**#{lead.get('id')} · {lead.get('name','Клиент')}**")
                c1.caption(f"{lead.get('created_at','')} · {lead.get('source','')}")
                c2.write(f"Контакт: {lead.get('contact','—')}")
                c2.caption(f"Товар: {lead.get('product','—')}")
                current = lead.get("status", "Новый")
                new_status = c3.selectbox("Статус", CRM_STATUSES, index=CRM_STATUSES.index(current) if current in CRM_STATUSES else 0, key=f"crm_status_{lead.get('id')}")
                if new_status != current:
                    update_lead(lead.get("id"), status=new_status)
                    st.rerun()
                if lead.get("message"):
                    st.caption(lead["message"])
    lead_stats = crm_metrics(load_leads())
    lc1, lc2, lc3 = st.columns(3)
    lc1.metric("Обращений", lead_stats.get("total", 0))
    lc2.metric("Новых", lead_stats.get("new", 0))
    lc3.metric("Заказов из CRM", lead_stats.get("orders", 0))
    st.caption("Ядро работает без платного AI API. Внешний AI можно подключить позже как дополнительный слой.")



if st.session_state.pop("open_max", False):
    max_dialog()

# ========== 7: НАСТРОЙКИ ==========
with tab7:
    st.markdown('<div class="section-kicker">WORKSPACE</div><div class="section-title">Настройки</div><div class="section-subtitle">Логотип, резервные копии и управление данными.</div>', unsafe_allow_html=True)

    st.subheader("Логотип магазина")
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

    st.subheader("Резервное копирование")
    products = load_products()
    plan = load_plan()
    backup = {"products": products, "content_plan": plan, "date": str(datetime.date.today())}
    st.download_button("⬇️ Скачать все данные (JSON)",
        json.dumps(backup, ensure_ascii=False, indent=2),
        file_name=f"arsenal_backup_{datetime.date.today()}.json", mime="application/json")

    st.markdown("---")
    st.subheader("Управление данными")
    if st.button("🗑️ Очистить каталог товаров"):
        save_products([])
        st.success("Каталог очищен!")
        st.rerun()
    if st.button("🗑️ Очистить контент-план"):
        save_plan([])
        st.success("План очищен!")
        st.rerun()

st.markdown("---")
st.caption("Arsenal Sport Content Studio v2.6 MAX · рабочее пространство магазина")
