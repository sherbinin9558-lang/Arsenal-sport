
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json, io, datetime, csv, requests, base64, re
from pathlib import Path
from max_features import product_search, catalog_metrics, auto_content_bundle, planner_suggestions, knowledge_answer
from crm_core import create_lead, crm_metrics, load_leads, update_lead, add_lead_interaction, set_customer_profile, STATUSES as CRM_STATUSES
from free_automation import load_orders, create_order, update_order, order_metrics, low_stock, customer_history, content_bundle, seven_day_plan, conversion_metrics
from automation_suite import low_stock_products, stock_info, content_for_product, make_30_day_plan, bulk_update, analytics as automation_analytics, save_uploaded_photo, product_key

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
    # Новые варианты.
    "Dark Premium":       {"bg": (9,12,18), "text": (248,249,252), "sec": (148,157,175), "accent": (105,120,255)},
    "Sport Performance":  {"bg": (8,16,27), "text": (248,250,255), "sec": (160,181,207), "accent": (65,160,255)},
    "Editorial Sport":    {"bg": (244,246,249), "text": (20,24,32), "sec": (91,99,113), "accent": (35,71,150)},
    "Black & Electric":   {"bg": (4,5,8), "text": (250,250,252), "sec": (135,140,151), "accent": (168,92,255)},
    # Совместимость со старыми сохранёнными товарами и Reels.
    "Спортивный":         {"bg": (18,25,36), "text": (245,247,250), "sec": (166,181,201), "accent": (105,164,235)},
    "Премиум":            {"bg": (18,20,27), "text": (239,242,247), "sec": (177,184,198), "accent": (137,125,255)},
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

def _fit_text_lines(draw, text, font, max_w, max_lines=2):
    words = (text or "").split()
    lines = []
    cur = ""
    for word in words:
        test = f"{cur} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines



def generate_card(image, name, brand, article, sizes, color, description, specs, category, template):
    # Единая профессиональная система Arsenal Sport с четырьмя визуальными направлениями.
    t = TEMPLATES.get(template, TEMPLATES["Dark Premium"])
    W, H = CARD_SIZE
    accent = t["accent"]
    light = template == "Editorial Sport"

    canvas = Image.new("RGB", CARD_SIZE, t["bg"])
    draw = ImageDraw.Draw(canvas)

    if light:
        # Editorial: чистый журнальный фон.
        draw.rectangle((0, 0, W, H), fill=t["bg"])
        draw.polygon([(0, 0), (W, 0), (W, 185), (0, 245)], fill=(232,235,240))
    else:
        # Премиальный тёмный градиент.
        top = t["bg"]
        bottom = tuple(min(255, x + 16) for x in t["bg"])
        for y in range(H):
            k = y / max(1, H - 1)
            c = tuple(int(top[i] * (1-k) + bottom[i] * k) for i in range(3))
            draw.line([(0, y), (W, y)], fill=c)

        # Мягкий световой акцент.
        glow_center = (W-230, 285)
        for r in range(390, 0, -15):
            k = 1 - r / 390
            c = tuple(min(255, int(t["bg"][i] + accent[i] * 0.10 * k)) for i in range(3))
            draw.ellipse((glow_center[0]-r, glow_center[1]-r, glow_center[0]+r, glow_center[1]+r), fill=c)

        # Динамика для спортивного и electric вариантов.
        if template == "Sport Performance":
            draw.polygon([(0, 0), (355, 0), (0, 245)], fill=(14, 28, 46))
            draw.line([(35, 230), (270, 0)], fill=accent, width=7)
            draw.line([(55, 245), (290, 15)], fill=(140, 195, 255), width=2)
            draw.polygon([(W, H), (W-350, H), (W, H-250)], fill=(13, 25, 42))
        elif template == "Black & Electric":
            draw.polygon([(0, 0), (250, 0), (0, 165)], fill=(16, 10, 27))
            draw.line([(48, 175), (220, 0)], fill=accent, width=5)
            draw.line([(W-210, H), (W, H-210)], fill=accent, width=3)
        else:
            draw.polygon([(0, 0), (300, 0), (0, 190)], fill=(20, 26, 39))
            draw.line([(55, 190), (240, 5)], fill=accent, width=4)

    # Брендинг.
    logo_img = get_logo()
    logo_w = 235 if light else 255
    if logo_img:
        ratio = logo_w / max(1, logo_img.width)
        lr = logo_img.resize((logo_w, int(logo_img.height * ratio)), Image.Resampling.LANCZOS)
        canvas.paste(lr, (60, 48), lr)
    else:
        draw.text((60, 55), "ARSENAL SPORT", font=get_font(36, True), fill=t["text"])

    # Категория.
    cat = category.upper()
    cat_font = get_font(22, True)
    cat_w = draw.textbbox((0, 0), cat, font=cat_font)[2]
    pill_x = W - cat_w - 72
    if light:
        draw.rounded_rectangle((pill_x-22, 50, W-52, 91), radius=20, fill=(226,230,236), outline=(188,194,204), width=1)
    else:
        draw.rounded_rectangle((pill_x-22, 50, W-52, 91), radius=20, fill=(30, 37, 51), outline=(70, 80, 105), width=1)
    draw.text((pill_x, 60), cat, font=cat_font, fill=t["sec"])

    # Фото — главный объект.
    if image:
        img = image.convert("RGB")
        iw, ih = img.size
        max_w, max_h = (910, 735) if not light else (900, 720)
        ratio = min(max_w / max(1, iw), max_h / max(1, ih))
        ns = (max(1, int(iw * ratio)), max(1, int(ih * ratio)))
        img = img.resize(ns, Image.Resampling.LANCZOS)
        x = (W - ns[0]) // 2
        y = 170 + max(0, (755 - ns[1]) // 2)

        shadow = Image.new("RGBA", (ns[0]+36, ns[1]+36), (0,0,0,0))
        sd = ImageDraw.Draw(shadow)
        sd.rounded_rectangle((18,18,ns[0]+18,ns[1]+18), radius=28, fill=(0,0,0,105))
        canvas.paste(shadow, (x-18, y-18), shadow)

        frame_color = (245,247,250) if light else (224,228,236)
        frame = Image.new("RGB", (ns[0]+12, ns[1]+12), frame_color)
        frame.paste(img, (6,6))
        canvas.paste(frame, (x-6, y-6))

        if template == "Editorial Sport":
            draw.line([(54, y+ns[1]+32), (300, y+ns[1]+32)], fill=accent, width=5)

    # Информационная панель.
    panel_y = 955
    panel_fill = (250,251,253) if light else (13,17,25)
    panel_outline = (210,214,221) if light else (52,61,79)
    draw.rounded_rectangle((44, panel_y, W-44, H-44), radius=34, fill=panel_fill, outline=panel_outline, width=2)
    draw.line([(76, panel_y+38), (235, panel_y+38)], fill=accent, width=5)

    brand_text = (brand or "ARSENAL SPORT").upper()
    draw.text((76, panel_y+62), brand_text[:28], font=get_font(25, True), fill=t["sec"])

    title_font = fit_font(draw, (name or "ТОВАР").upper(), 860, max_size=58, min_size=34)
    title_lines = _fit_text_lines(draw, (name or "ТОВАР").upper(), title_font, 860, 2)
    ty = panel_y + 104
    for line in title_lines:
        draw.text((76, ty), line, font=title_font, fill=t["text"])
        ty += title_font.size + 4

    meta = []
    if color: meta.append(str(color))
    if sizes: meta.append(f"Размеры {sizes}")
    if article: meta.append(f"арт. {article}")
    meta_text = "  •  ".join(meta)
    if meta_text:
        draw.text((76, H-108), meta_text[:70], font=get_font(22), fill=t["sec"])

    draw.text((W-310, H-108), "ARSENAL SPORT", font=get_font(21, True), fill=accent)
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
def _telegram_chat_id(raw_channel):
    value = str(raw_channel or "").strip()
    if value.startswith("https://t.me/"):
        value = value.rstrip("/").split("/")[-1]
    if value.startswith("t.me/"):
        value = value.rstrip("/").split("/")[-1]
    if value.startswith("-100") or value.lstrip("-").isdigit():
        return value
    return value if value.startswith("@") else "@" + value

def _telegram_api(token, method):
    return f"https://api.telegram.org/bot{token}/{method}"

def publish_reel_to_telegram(video_bytes, caption):
    try:
        token = str(st.secrets["TELEGRAM_TOKEN"]).strip()
        channel = _telegram_chat_id(st.secrets["TELEGRAM_CHANNEL"])
        if not token:
            return False, "TELEGRAM_TOKEN пустой."
        if not channel:
            return False, "TELEGRAM_CHANNEL пустой."

        size_mb = len(video_bytes) / (1024 * 1024)
        if size_mb > 50:
            return False, f"Видео весит {size_mb:.1f} МБ — больше лимита Telegram Bot API 50 МБ."

        caption = (caption or "").strip()[:1024]
        api_url = _telegram_api(token, "sendVideo")

        files = {
            "video": ("arsenal_sport_reel.mp4", video_bytes, "video/mp4")
        }
        data = {
            "chat_id": channel,
            "caption": caption,
            "supports_streaming": "true",
        }

        resp = requests.post(
            api_url,
            files=files,
            data=data,
            timeout=(20, 300),
        )

        try:
            result = resp.json()
        except Exception:
            result = {}

        if resp.ok and result.get("ok") is True:
            return True, f"Reels опубликован в Telegram ({channel}). Размер: {size_mb:.1f} МБ."

        description = result.get("description") or resp.text or "неизвестная ошибка"
        lower = description.lower()

        if "chat not found" in lower:
            return False, "Telegram не нашёл канал. Проверь TELEGRAM_CHANNEL: @username канала или числовой ID вида -100xxxxxxxxxx."
        if "not enough rights" in lower or "forbidden" in lower:
            return False, "Бот найден, но Telegram запретил публикацию. Бот должен быть администратором канала с правом публикации сообщений."
        if "file is too big" in lower:
            return False, f"Telegram отклонил видео как слишком большое ({size_mb:.1f} МБ)."
        if "wrong file identifier/http url specified" in lower:
            return False, f"Telegram не принял MP4. Размер {size_mb:.1f} МБ. Ответ API: {description}"

        # Резервный канал: если sendVideo не прошёл из-за формата/обработки,
        # пробуем загрузить тот же MP4 как документ. Это позволяет не терять файл
        # и одновременно показывает, что проблема именно в обработке video Telegram.
        try:
            doc_resp = requests.post(
                _telegram_api(token, "sendDocument"),
                files={"document": ("arsenal_sport_reel.mp4", video_bytes, "video/mp4")},
                data={
                    "chat_id": channel,
                    "caption": caption,
                },
                timeout=(20, 300),
            )
            try:
                doc_result = doc_resp.json()
            except Exception:
                doc_result = {}

            if doc_resp.ok and doc_result.get("ok") is True:
                return True, (
                    f"Telegram не принял файл как видео, поэтому отправил его как MP4-документ. "
                    f"Размер: {size_mb:.1f} МБ. Причина sendVideo: {description}"
                )
        except requests.RequestException:
            pass

        return False, f"Telegram API не принял Reels: {description} (HTTP {resp.status_code}, {size_mb:.1f} МБ)."

    except KeyError as e:
        return False, f"Не найден секрет: {e}. Нужны TELEGRAM_TOKEN и TELEGRAM_CHANNEL."
    except requests.RequestException as e:
        return False, f"Сеть/Telegram недоступны: {e}"
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
st.set_page_config(page_title="Arsenal Sport Content Manager", layout="wide")

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
.block-container {padding-top:0.15rem!important;}\n .main-title {font-size:2.45rem;font-weight:850;color:#f5f7fa;text-align:center;margin:0 0 0;letter-spacing:.02em;}
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

st.markdown('<p class="main-title">ARSENAL SPORT</p>', unsafe_allow_html=True)
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


# ==================== МАССОВЫЙ ИМПОРТ ====================
BULK_FIELDS = ["name", "brand", "article", "sizes", "color", "category", "description", "specs"]

def _bulk_value(row, *keys):
    normalized = {str(k).strip().lower().replace(" ", "_"): v for k, v in row.items()}
    aliases = {
        "name": ["name", "название", "товар"],
        "brand": ["brand", "бренд"],
        "article": ["article", "артикул"],
        "sizes": ["sizes", "размеры", "размер"],
        "color": ["color", "цвет"],
        "category": ["category", "категория"],
        "description": ["description", "описание"],
        "specs": ["specs", "характеристики"],
    }
    for key in keys:
        for alias in aliases.get(key, [key]):
            value = normalized.get(alias)
            if value is not None and str(value).strip():
                return str(value).strip()
    return ""

def parse_bulk_file(uploaded_file):
    raw = uploaded_file.getvalue()
    name = (uploaded_file.name or "").lower()

    if name.endswith(".xlsx"):
        try:
            from openpyxl import load_workbook
        except ImportError:
            raise RuntimeError("Для XLSX нужен openpyxl. CSV можно загружать без дополнительных зависимостей.")
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(x or "").strip() for x in rows[0]]
        return [dict(zip(headers, row)) for row in rows[1:] if any(x not in (None, "") for x in row)]

    text = raw.decode("utf-8-sig")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\\t,")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    return [dict(row) for row in reader if any(str(v or "").strip() for v in row.values())]

def bulk_import_products(uploaded_file, update_existing=False):
    rows = parse_bulk_file(uploaded_file)
    products = load_products()
    existing = {
        str(p.get("article", "")).strip().lower(): i
        for i, p in enumerate(products)
        if str(p.get("article", "")).strip()
    }
    added = updated = skipped = 0
    errors = []

    for line_no, row in enumerate(rows, start=2):
        name = _bulk_value(row, "name")
        brand = _bulk_value(row, "brand")
        article = _bulk_value(row, "article")
        if not name:
            skipped += 1
            errors.append(f"Строка {line_no}: нет названия.")
            continue

        category = _bulk_value(row, "category") or "Другое"
        if category not in CATEGORIES:
            category = "Другое"

        product = {
            "name": name,
            "brand": brand,
            "article": article,
            "sizes": _bulk_value(row, "sizes"),
            "color": _bulk_value(row, "color"),
            "description": _bulk_value(row, "description"),
            "specs": _bulk_value(row, "specs"),
            "category": category,
            "date_added": str(datetime.date.today()),
        }

        key = article.lower()
        if update_existing and key and key in existing:
            products[existing[key]].update(product)
            updated += 1
        else:
            products.append(product)
            if key:
                existing[key] = len(products) - 1
            added += 1

    save_products(products)
    return added, updated, skipped, errors


# ========== 2: КАТАЛОГ ==========
with tab2:
    st.markdown('<div class="section-kicker">PRODUCT LIBRARY</div><div class="section-title">Каталог</div><div class="section-subtitle">Все товары и готовые материалы — в одном рабочем пространстве.</div>', unsafe_allow_html=True)
    st.info("➕ Для нового товара откройте вкладку «📸 Создать».")

    st.markdown("### 📥 Массовая загрузка товаров")
    st.caption("Загрузите CSV или XLSX — товары добавятся в каталог без удаления существующих.")
    template_csv = io.StringIO()
    writer = csv.writer(template_csv, delimiter=";")
    writer.writerow(["Название", "Бренд", "Артикул", "Размеры", "Цвет", "Категория", "Описание", "Характеристики"])
    writer.writerow(["Футбольная форма", "Пример", "ART-001", "S,M,L,XL", "Чёрный", "Другое", "Описание товара", "Материал, особенности"])
    st.download_button(
        "⬇️ Скачать шаблон CSV",
        template_csv.getvalue().encode("utf-8-sig"),
        file_name="arsenal_sport_products_template.csv",
        mime="text/csv",
        key="bulk_template_csv",
    )
    bulk_file = st.file_uploader(
        "Файл с товарами",
        type=["csv", "xlsx"],
        key="bulk_products_file",
        help="В CSV используйте первую строку как названия колонок. Для XLSX — первая строка должна содержать заголовки.",
    )
    bulk_update = st.checkbox("Обновлять существующие товары по артикулу", value=False, key="bulk_update_existing")
    if bulk_file and st.button("📦 Импортировать товары", type="primary", key="bulk_import_btn"):
        try:
            added, updated, skipped, errors = bulk_import_products(bulk_file, bulk_update)
            st.success(f"Готово: добавлено {added}, обновлено {updated}, пропущено {skipped}.")
            if errors:
                with st.expander("⚠️ Строки с ошибками"):
                    for err in errors[:50]:
                        st.write(err)
            st.rerun()
        except Exception as e:
            st.error(f"Не удалось импортировать файл: {e}")

    st.markdown("---")
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

            # ВАЖНО: сохраняем MP4 в session_state. Streamlit перезапускает
            # скрипт при нажатии кнопки публикации, поэтому локальная переменная
            # video_bytes иначе теряется.
            st.session_state["reel_video_bytes"] = video_bytes
            st.session_state["reel_caption"] = gen_instagram(reel_product, "Продающий")
            st.session_state["reel_product_name"] = (
                f"{reel_product.get('brand','')} {reel_product.get('name','')}".strip()
            )
            st.success("✅ Reels создан и сохранён. Теперь можно публиковать.")

        # После создания MP4 этот блок остаётся доступным на следующих rerun.
        video_bytes = st.session_state.get("reel_video_bytes")
        reel_caption = st.session_state.get("reel_caption", "")
        reel_product_name = st.session_state.get("reel_product_name", "")

        if video_bytes:
            st.video(video_bytes, width=260)

            st.download_button(
                "⬇️ Скачать рилс",
                video_bytes,
                "reel.mp4",
                "video/mp4",
                key="dl_reel"
            )

            st.markdown("### 📤 Опубликовать Reels")
            if reel_product_name:
                st.caption(f"Товар: {reel_product_name}")

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
    qty, _, known = stock_info(product)
    return qty if known and qty is not None else 0

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
        if d < today:
            overdue.append(item)
        elif d == today:
            due.append(item)
    return due, overdue

def render_max():
    @st.dialog("⚡ Arsenal Sport MAX", width="large")
    def dialog():
        products = load_products()
        plan = load_plan()
        leads = load_leads()
        orders = load_orders()
        due, overdue = max_due_content(plan)
        crm = crm_metrics(leads)
        om = order_metrics(orders, ACTIVE_ORDER_STATUSES)
        low = low_stock_products(products)
        cm = conversion_metrics(leads, orders)

        st.caption("Бесплатный центр управления магазином: каталог, контент, заявки, заказы и продажи.")

        a, b, c, d, e = st.columns(5)
        a.metric("Товары", len(products))
        b.metric("Заявки", crm.get("total", 0))
        c.metric("Активные заказы", om["active"])
        d.metric("Контент сегодня", len(due))
        e.metric("Конверсия", f"{cm['conversion']:.1f}%")

        st.markdown("---")
        section = st.radio(
            "Раздел MAX",
            ["Обзор", "AI-продавец", "CRM", "Заказы", "Склад", "Контент", "Автоматизация", "Аналитика"],
            horizontal=True,
            key="max_section",
        )

        if section == "Обзор":
            st.subheader("Состояние магазина")
            x, y, z = st.columns(3)
            x.metric("Всего заказов", om["total"])
            y.metric("Завершено", om["completed"])
            z.metric("Сумма заказов", f"{om['amount']:,.0f}".replace(",", " ") + " ₽")
            st.write(
                f"Товаров: {len(products)} · карточек: "
                f"{sum(bool(p.get('card_image')) for p in products)} · "
                f"публикаций в плане: {len(plan)}"
            )
            if overdue:
                st.error(f"Просрочено публикаций: {len(overdue)}")
            elif due:
                st.info(f"На сегодня: {len(due)} публикаций")
            else:
                st.success("На сегодня срочных публикаций нет.")
            if low:
                st.warning(f"Низкий остаток: {len(low)} товаров (порог ≤ 2).")

        elif section == "AI-продавец":
            st.subheader("AI-продавец по каталогу")
            q = st.text_input(
                "Что ищет клиент?",
                placeholder="Например: бутсы 42 размера",
                key="max_sales_query",
            )
            if st.button("🔎 Найти товар", type="primary", key="max_sales_search"):
                ans, found = ai_sales_reply(products, q)
                st.session_state["max_sales_answer"] = ans
                st.session_state["max_sales_found"] = found
            if st.session_state.get("max_sales_answer"):
                st.text_area("Готовый ответ", st.session_state["max_sales_answer"], height=180, key="max_sales_answer_box")
            found = st.session_state.get("max_sales_found", [])
            if found:
                follow = st.text_input("Уточнение клиента", placeholder="Например: покажи второй вариант", key="max_followup")
                if st.button("↩️ Ответить клиенту", key="max_followup_btn"):
                    ans, new_found = sales_followup(products, follow, found)
                    st.session_state["max_sales_answer"] = ans
                    st.session_state["max_sales_found"] = new_found
                    st.rerun()

        elif section == "CRM":
            st.subheader("CRM — заявки и история")
            if not leads:
                st.info("Заявок пока нет.")
            for lead in reversed(leads[-20:]):
                title = lead.get("name") or lead.get("contact") or f"Заявка #{lead.get('id', '')}"
                with st.expander(f"{title} · {lead.get('status', 'Новый')}"):
                    st.write(f"Контакт: {lead.get('contact', '—')}")
                    st.write(f"Товар: {lead.get('product', '—')}")
                    st.write(f"Источник: {lead.get('source', '—')}")
                    st.write(f"Сообщение: {lead.get('message', '—')}")
                    if lead.get("history"):
                        st.caption("История контакта")
                        for h in lead.get("history", [])[-10:]:
                            st.write(f"{h.get('time','')} · {h.get('direction','')} · {h.get('message','')}")
                    current_status = lead.get("status", "Новый")
                    ns = st.selectbox(
                        "Статус", CRM_STATUSES,
                        index=CRM_STATUSES.index(current_status) if current_status in CRM_STATUSES else 0,
                        key=f"max_lead_status_{lead.get('id')}",
                    )
                    if ns != current_status:
                        update_lead(lead.get("id"), status=ns)
                        st.rerun()
                    note = st.text_input("Добавить заметку/контакт", key=f"max_note_{lead.get('id')}")
                    if st.button("💾 Сохранить заметку", key=f"max_note_btn_{lead.get('id')}"):
                        if note.strip():
                            add_lead_interaction(lead.get("id"), note.strip(), "manager")
                            st.rerun()
            st.markdown("---")
            history_q = st.text_input("Найти историю клиента по имени/контакту", key="max_history_q")
            if history_q:
                history = customer_history(leads, orders, history_q)
                if not history:
                    st.info("Совпадений не найдено.")
                for kind, item in history:
                    st.write(f"**{'Заявка' if kind == 'lead' else 'Заказ'} #{item.get('id','')}** · {item.get('created_at','')} · {item.get('product','')}")

        elif section == "Заказы":
            st.subheader("Заказы — бесплатно, локально")
            with st.form("max_new_order", clear_on_submit=True):
                o1, o2 = st.columns(2)
                with o1:
                    customer = st.text_input("Клиент")
                    contact = st.text_input("Контакт")
                    product_name = st.text_input("Товар")
                with o2:
                    amount = st.text_input("Сумма, ₽")
                    status = st.selectbox("Статус", ORDER_STATUSES)
                    source = st.selectbox("Источник", ["Manual", "Telegram", "Instagram", "VK", "Другое"])
                if st.form_submit_button("➕ Создать заказ"):
                    create_order(customer, contact, product_name, amount=amount, status=status, source=source)
                    st.success("Заказ создан.")
                    st.rerun()

            if not orders:
                st.info("Заказов пока нет.")
            for order in reversed(orders[-30:]):
                title = f"#{order.get('id','')} · {order.get('customer') or order.get('contact') or 'Клиент'} · {order.get('product') or 'Товар'}"
                with st.expander(title):
                    st.write(f"Контакт: {order.get('contact','—')} · Сумма: {order.get('amount','—')} ₽")
                    current = order.get("status", "Новая")
                    ns = st.selectbox("Статус заказа", ORDER_STATUSES,
                                      index=ORDER_STATUSES.index(current) if current in ORDER_STATUSES else 0,
                                      key=f"max_order_status_{order.get('id')}")
                    if ns != current:
                        update_order(order.get("id"), status=ns)
                        st.rerun()

        elif section == "Автоматизация":
            st.subheader("🚀 Центр автоматизации Arsenal Sport")
            st.caption("Бесплатный локальный контур: массовые фото, контент, склад, план на 30 дней, массовое редактирование и аналитика.")

            auto_tab1, auto_tab2, auto_tab3, auto_tab4 = st.tabs(["📸 Фото", "✍️ Контент", "📦 Каталог", "📊 Аналитика"])

            with auto_tab1:
                st.markdown("### Массовая обработка фотографий")
                st.caption("Названия файлов лучше делать по артикулу: например ART-001.jpg. Фото сохраняются отдельно и не заменяют исходный каталог.")
                photo_files = st.file_uploader(
                    "Загрузите несколько фото",
                    type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=True,
                    key="auto_photos",
                )
                if photo_files:
                    names = [f.name for f in photo_files]
                    st.write("Файлов загружено:", len(names))
                    if st.button("📸 Привязать фото к товарам", type="primary", key="auto_match_photos"):
                        products_now = load_products()
                        matched = 0
                        skipped = []
                        articles = {str(p.get("article","")).strip().lower(): i for i,p in enumerate(products_now) if str(p.get("article","")).strip()}
                        for f in photo_files:
                            stem = Path(f.name).stem.strip().lower()
                            idx = articles.get(stem)
                            if idx is None:
                                for i,p in enumerate(products_now):
                                    key = product_key(p, i).lower()
                                    if stem == key or stem in key:
                                        idx = i
                                        break
                            if idx is None:
                                skipped.append(f.name)
                                continue
                            path = save_uploaded_photo(f, products_now[idx], idx)
                            products_now[idx]["original_image"] = path
                            try:
                                source_img = Image.open(io.BytesIO(f.getvalue())).convert("RGB")
                                p_now = products_now[idx]
                                card_img = generate_card(
                                    source_img,
                                    p_now.get("name",""),
                                    p_now.get("brand",""),
                                    p_now.get("article",""),
                                    p_now.get("sizes",""),
                                    p_now.get("color",""),
                                    p_now.get("description",""),
                                    p_now.get("specs",""),
                                    p_now.get("category","Другое"),
                                    "Dark Premium",
                                )
                                card_buf = io.BytesIO()
                                card_img.save(card_buf, format="PNG")
                                products_now[idx]["card_image"] = base64.b64encode(card_buf.getvalue()).decode("ascii")
                            except Exception:
                                pass
                            matched += 1
                        save_products(products_now)
                        st.success(f"Готово: привязано {matched}, не найдено {len(skipped)}.")
                        if skipped:
                            st.caption("Не сопоставлены: " + ", ".join(skipped[:20]))
                        st.rerun()

            with auto_tab2:
                st.markdown("### Массовый контент")
                st.caption("Генерация выполняется без платного API. Тексты можно сразу использовать для Instagram, Telegram, VK, Stories и Reels.")
                if not products:
                    st.info("Сначала добавьте товары в каталог.")
                else:
                    limit = st.slider("Сколько товаров обработать", 1, min(100, len(products)), min(30, len(products)), key="auto_content_limit")
                    if st.button("✍️ Создать контент для выбранного количества", type="primary", key="auto_content_btn"):
                        bundles = {}
                        for i,p in enumerate(products[:limit]):
                            bundles[str(i)] = {"product": max_product_title(p), "content": content_for_product(p)}
                        st.session_state["auto_content_bundles"] = bundles
                        st.success(f"Контент подготовлен для {limit} товаров.")
                    bundles = st.session_state.get("auto_content_bundles", {})
                    if bundles:
                        for item in list(bundles.values())[:10]:
                            with st.expander(item["product"]):
                                for channel, value in item["content"].items():
                                    st.markdown(f"**{channel}**")
                                    st.text_area(channel, value, height=120, key=f"auto_text_{item['product']}_{channel}")

                st.markdown("---")
                st.markdown("### 📅 План на 30 дней")
                if st.button("📅 Создать 30-дневный контент-план", type="primary", key="auto_30_plan"):
                    generated = make_30_day_plan(products)
                    existing = load_plan()
                    existing_keys = {(x.get("date"), x.get("product"), x.get("platform"), x.get("type")) for x in existing}
                    added = 0
                    for item in generated:
                        key = (item["date"], item["product"], item["platform"], item["type"])
                        if key not in existing_keys:
                            existing.append(item)
                            added += 1
                    save_plan(existing)
                    st.success(f"Добавлено {added} публикаций без дублей.")
                    st.rerun()

            with auto_tab3:
                st.markdown("### Массовое редактирование")
                if products:
                    labels = [f"{i+1}. {max_product_title(p)}" for i,p in enumerate(products)]
                    selected = st.multiselect("Товары", labels, key="auto_bulk_products")
                    indexes = [labels.index(x) for x in selected]
                    field = st.selectbox("Что изменить", ["category", "brand", "sizes", "color"], key="auto_bulk_field")
                    if field == "category":
                        value = st.selectbox("Новое значение", CATEGORIES, key="auto_bulk_value_cat")
                    else:
                        value = st.text_input("Новое значение", key="auto_bulk_value_text")
                    if st.button("✏️ Применить к выбранным", type="primary", key="auto_bulk_apply"):
                        if not indexes:
                            st.warning("Выберите хотя бы один товар.")
                        elif not str(value).strip():
                            st.warning("Значение не должно быть пустым.")
                        else:
                            products_now = load_products()
                            changed = bulk_update(products_now, indexes, field, value.strip())
                            save_products(products_now)
                            st.success(f"Изменено товаров: {changed}.")
                            st.rerun()
                else:
                    st.info("Каталог пуст.")

                st.markdown("---")
                st.markdown("### 📦 Остатки по размерам")
                if products:
                    stock_labels = [f"{i+1}. {max_product_title(p)}" for i,p in enumerate(products)]
                    stock_choice = st.selectbox("Товар", stock_labels, key="auto_stock_product")
                    stock_idx = stock_labels.index(stock_choice)
                    sp = products[stock_idx]
                    current_stock = sp.get("stock_by_size") if isinstance(sp.get("stock_by_size"), dict) else {}
                    raw_sizes = str(sp.get("sizes","")).replace(";", ",")
                    sizes_list = [x.strip() for x in raw_sizes.split(",") if x.strip()]
                    if not sizes_list and current_stock:
                        sizes_list = list(current_stock.keys())
                    if not sizes_list:
                        sizes_list = ["S", "M", "L", "XL"]
                    st.caption("Введите количество через запятую в порядке размеров: " + ", ".join(sizes_list))
                    qty_text = st.text_input("Количество", value=", ".join(str(current_stock.get(s, 0)) for s in sizes_list), key="auto_stock_qty")
                    if st.button("💾 Сохранить остатки", key="auto_stock_save"):
                        parts = [x.strip() for x in qty_text.split(",")]
                        stock = {}
                        for i,size in enumerate(sizes_list):
                            try: stock[size] = max(0, int(parts[i])) if i < len(parts) else 0
                            except Exception: stock[size] = 0
                        products_now = load_products()
                        products_now[stock_idx]["stock_by_size"] = stock
                        products_now[stock_idx]["total_stock"] = sum(stock.values())
                        save_products(products_now)
                        st.success("Остатки сохранены.")
                        st.rerun()

            with auto_tab4:
                st.markdown("### Аналитика магазина")
                a = automation_analytics(products, leads, orders, plan)
                q1,q2,q3,q4 = st.columns(4)
                q1.metric("Товары", a["products"])
                q2.metric("Заявки", a["leads"])
                q3.metric("Заказы", a["orders"])
                q4.metric("В плане", a["plan"])
                st.markdown("**Категории**")
                for name,count in a["categories"]:
                    st.write(f"• {name}: {count}")
                st.markdown("**Источники заявок**")
                if a["sources"]:
                    for name,count in a["sources"]:
                        st.write(f"• {name}: {count}")
                else:
                    st.caption("Пока нет заявок.")
                st.markdown("**Товары в заказах**")
                if a["top_products"]:
                    for name,count in a["top_products"]:
                        st.write(f"• {name}: {count}")
                else:
                    st.caption("Пока нет заказов.")

                st.markdown("---")
                st.markdown("### 🔎 Умный поиск")
                query = st.text_input("Например: бутсы 42 искусственное поле", key="auto_smart_search")
                if query:
                    found = product_search(products, query)
                    if found:
                        for p in found[:20]:
                            qty, _, known = stock_info(p)
                            stock_text = str(qty) if known and qty is not None else "не указан"
                            st.write(f"**{max_product_title(p)}** · {p.get('sizes','—')} · остаток: {stock_text}")
                    else:
                        st.info("Подходящих товаров не найдено.")

                st.markdown("---")
                st.markdown("### ⚡ Быстрый запуск")
                st.caption("Запускает бесплатный контент-конвейер для всего каталога: тексты + план на 30 дней. Фото остаются отдельным шагом, чтобы не перезаписывать исходные файлы.")
                if st.button("⚡ Запустить автоматизацию", type="primary", key="auto_run_all"):
                    generated = make_30_day_plan(products)
                    existing = load_plan()
                    existing_keys = {(x.get("date"), x.get("product"), x.get("platform"), x.get("type")) for x in existing}
                    for item in generated:
                        key = (item["date"], item["product"], item["platform"], item["type"])
                        if key not in existing_keys:
                            existing.append(item)
                    save_plan(existing)
                    st.session_state["auto_content_bundles"] = {
                        str(i): {"product": max_product_title(p), "content": content_for_product(p)}
                        for i,p in enumerate(products)
                    }
                    st.success("Готово: контент подготовлен, план на 30 дней сформирован.")

        elif section == "Склад":
            st.subheader("Склад и контроль остатков")
            if not products:
                st.info("Каталог пуст.")
            else:
                if low:
                    st.warning("Товары с остатком 0–2:")
                    for p, qty in low:
                        st.write(f"• {max_product_title(p)} — **{qty} шт.**")
                else:
                    st.success("Товаров с остатком ≤ 2 нет.")
                st.caption("Товары без заданного остатка не считаются дефицитными.")
                for p in products[:30]:
                    qty, _, known = stock_info(p)
                    st.write(f"{max_product_title(p)} — {qty if known and qty is not None else '—'} шт.")

        elif section == "Контент":
            st.subheader("Контент без платного AI")
            if not products:
                st.info("Сначала добавьте товар в каталог.")
            else:
                names = [max_product_title(p) for p in products]
                sel = st.selectbox("Товар", names, key="max_content_product")
                p = products[names.index(sel)]
                bundle = content_bundle(p)
                for channel, text_value in bundle.items():
                    st.markdown(f"**{channel}**")
                    st.text_area(channel, text_value, height=110, key=f"max_bundle_{channel}")
                if st.button("✨ Создать 7 идей и добавить в план", type="primary", key="max_plan_suggest"):
                    suggestions = seven_day_plan(products)
                    existing = load_plan()
                    for item in suggestions:
                        if not any(x.get("date") == item["date"] and x.get("product") == item["product"] for x in existing):
                            existing.append(item)
                    save_plan(existing)
                    st.success("План на 7 дней добавлен без дублей.")
                    st.rerun()

        else:
            st.subheader("Аналитика")
            x, y, z = st.columns(3)
            x.metric("Заявки", cm["leads"])
            y.metric("Заказов из CRM", cm["lead_orders"])
            z.metric("Конверсия заявка → заказ", f"{cm['conversion']:.1f}%")
            st.markdown("---")
            st.write(f"Всего заказов: **{om['total']}**")
            st.write(f"Активных: **{om['active']}**")
            st.write(f"Завершённых: **{om['completed']}**")
            st.write(f"Отменённых: **{om['cancelled']}**")
            st.write(f"Сумма неотменённых заказов: **{om['amount']:,.0f} ₽**".replace(",", " "))
            st.markdown("---")
            st.write("Категории каталога:")
            counts = {}
            for p in products:
                cat = p.get("category", "Другое")
                counts[cat] = counts.get(cat, 0) + 1
            for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
                st.write(f"• {cat}: {count}")

        if st.button("Закрыть MAX", key="close_max"):
            st.session_state["open_max"] = False
            st.rerun()

    dialog()

if st.session_state.get("open_max", False):
    render_max()
