
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import json, io, datetime, csv, requests, base64, re, tempfile, os
from pathlib import Path
from max_features import product_search, catalog_metrics, auto_content_bundle, planner_suggestions, knowledge_answer
from crm_core import create_lead, crm_metrics, load_leads, update_lead, add_lead_interaction, set_customer_profile, STATUSES as CRM_STATUSES
from free_automation import load_orders, create_order, update_order, order_metrics, low_stock, customer_history, content_bundle, seven_day_plan, conversion_metrics
from automation_suite import low_stock_products, stock_info, content_for_product, make_30_day_plan, bulk_update, analytics as automation_analytics, save_uploaded_photo, product_key
from content_manager import WORKFLOW_STATUSES, ensure_workflow, change_status, adapt_content, workflow_metrics, recommendations, report_lines
from growth_engine import ai_summary, attribution_performance

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
STATUSES = WORKFLOW_STATUSES
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

ATTRIBUTION_FILE = Path("content_attribution.json")

def load_attribution():
    return load_json(ATTRIBUTION_FILE, [])

def save_attribution(items):
    save_json(ATTRIBUTION_FILE, items)

def attribution_metrics(attribution, leads, orders):
    by_product = {}
    for item in attribution:
        key = str(item.get("product_id") or item.get("product") or "")
        if not key:
            continue
        row = by_product.setdefault(key, {"content": 0, "leads": 0, "orders": 0})
        row["content"] += 1
        row["leads"] += int(item.get("leads", 0) or 0)
        row["orders"] += int(item.get("orders", 0) or 0)
    return by_product

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



from card_generator import generate_card

# ==================== ТЕКСТЫ ====================
def make_hashtags(name, brand, category):
    base = ["#ai_agent_content_manager", "#спорт", "#экипировка", "#новинка"]
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
        "Официальный": "Новая позиция в AI Agent Content Manager — " + n,
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

📩 Напишите нам в сообщения AI Agent Content Manager — поможем подобрать размер и оформить заказ.

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
        "Официальный": "🏆 Новое поступление в AI Agent Content Manager",
        "Дружеский": "🎉 Ребята, смотрите, что приехало!",
        "Продающий": "🔥 НОВИНКА В AI AGENT CONTENT MANAGER"
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
            "video": ("ai_agent_content_manager_reel.mp4", video_bytes, "video/mp4")
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
                files={"document": ("ai_agent_content_manager_reel.mp4", video_bytes, "video/mp4")},
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
            "name": "AI Agent Content Manager Reels",
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
st.set_page_config(page_title="AI Agent Content Manager", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

with st.sidebar:
    st.markdown('<div class="sidebar-ai-agent">AI агент контент менеджер</div>', unsafe_allow_html=True)
    st.title("AI Agent Content Manager")
    st.caption("Content Studio · v2.6 MAX")
    dark_mode = st.toggle("🌙 Тёмная тема", value=False, key="theme_toggle")
    st.markdown("---")
    st.markdown(
        '<div class="sidebar-max"><div class="sidebar-max-kicker">AI AGENT CONTENT MANAGER</div>'
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
    .stApp {background:#f6f7fb!important;color:#171a21!important;}
    section[data-testid="stSidebar"] {background:#ffffff!important;border-right:1px solid #e4e7ec!important;}
    div[data-baseweb="tab-list"] {background:#ffffff!important;border-color:#e1e5eb!important;}
    [data-testid="stFileUploader"] {background:#f5f7fa!important;border-color:#b9c1ce!important;}
    .sidebar-max {background:linear-gradient(135deg,#f5f2ff,#e9e5ff);border-color:#c9c1ff;}
    .sidebar-max-kicker {color:#5b4bd6;}
    .sidebar-max-title {color:#21164d;}
    .sidebar-max-text {color:#5f6472;}
    .stApp, .stApp * {color:#17151c;}
    .stApp [data-testid="stMarkdownContainer"] p, .stApp [data-testid="stMarkdownContainer"] li, .stApp [data-testid="stMarkdownContainer"] span, .stApp label, .stApp [data-testid="stCaptionContainer"] {color:#17151c !important;}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {color:#17151c !important;}
    .stApp input, .stApp textarea, .stApp [data-baseweb="select"] * {color:#17151c !important;}
    .stApp input::placeholder, .stApp textarea::placeholder {color:#667080 !important;opacity:1 !important;}
    .stApp button:not([data-baseweb="tab"]) {color:#17151c !important;}
    .stApp button[kind="primary"] {color:#ffffff !important;}
    button[data-baseweb="tab"] {color:#17151c !important;background:#ffffff !important;border-color:#dfe3ea !important;}
    button[data-baseweb="tab"] * {color:#17151c !important;}
    button[data-baseweb="tab"][aria-selected="true"] {color:#32165f !important;background:linear-gradient(135deg,#f1eaff,#e8ddff) !important;border-color:#bda6e8 !important;box-shadow:0 0 0 1px rgba(72,35,125,.16),0 0 11px rgba(83,43,145,.18) !important;}
    button[data-baseweb="tab"][aria-selected="true"] * {color:#32165f !important;}
    .section-kicker {color:#4b247c !important;text-shadow:0 0 7px rgba(75,36,124,.22) !important;}
    .pill {color:#32165f !important;}
    /* Light theme: transparent controls/cards so black text stays readable. */
    .stApp .stButton > button:not([kind="primary"]) {background:transparent !important;color:#17151c !important;border-color:#cfd4dd !important;box-shadow:none !important;}
    .stApp .stButton > button:not([kind="primary"]):hover {background:rgba(91,70,214,.05) !important;color:#17151c !important;border-color:#8b7bc7 !important;box-shadow:0 0 0 1px rgba(75,36,124,.12) !important;}
    div[data-baseweb="tab-list"] {background:transparent !important;box-shadow:none !important;border-color:#dfe3ea !important;}
    button[data-baseweb="tab"] {background:transparent !important;color:#17151c !important;border-color:transparent !important;box-shadow:none !important;}
    button[data-baseweb="tab"] * {color:#17151c !important;}
    button[data-baseweb="tab"][aria-selected="true"] {background:rgba(232,221,255,.55) !important;color:#32165f !important;border-color:#bda6e8 !important;box-shadow:0 0 0 1px rgba(72,35,125,.12),0 0 10px rgba(83,43,145,.12) !important;}
    button[data-baseweb="tab"][aria-selected="true"] * {color:#32165f !important;}
    .stat-box {background:transparent !important;color:#17151c !important;border:1px solid #dfe3ea !important;box-shadow:none !important;}
    .stat-number {color:#17151c !important;}
    .stat-label {color:#596174 !important;}
    [data-testid="stAlert"], div[data-baseweb="notification"] {background:transparent !important;color:#17151c !important;border-color:#dfe3ea !important;}
    [data-testid="stAlert"] *, div[data-baseweb="notification"] * {color:#17151c !important;}

    """

st.markdown(
    "<style>\n" + bg_css + theme_css + """
/* Hide Streamlit platform controls from the customer-facing UI. */
#MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], footer {display:none !important;visibility:hidden !important;height:0 !important;min-height:0 !important;pointer-events:none !important;}\n/* Remove mobile bottom platform chrome; keep only app controls. */\n[data-testid="stBottom"], [data-testid="stBottomBlockContainer"], [data-testid="stBottomBlock"] {display:none !important;visibility:hidden !important;height:0 !important;min-height:0 !important;pointer-events:none !important;}\n# Hide repository / platform navigation links and icons from the customer UI.
# This affects only Streamlit chrome; MAX, sidebar and app controls remain intact.
a[href*="github.com"], a[href*="gitlab.com"], a[href*="bitbucket.org"],
a[aria-label*="GitHub" i], a[title*="GitHub" i],
a[aria-label*="Settings" i], a[title*="Settings" i],
[data-testid="stToolbar"] *, [data-testid="stDecoration"] *,
[data-testid="stStatusWidget"] *, [data-testid="stAppDeployButton"] * {
    display:none !important; visibility:hidden !important; pointer-events:none !important;
}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], footer,
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"], [data-testid="stBottomBlock"] {
    display:none !important; visibility:hidden !important; height:0 !important; min-height:0 !important;
    pointer-events:none !important;
}
section[data-testid="stSidebar"] {display:block !important; visibility:visible !important; opacity:1 !important;}
/* MAX popup controls: keep the launcher, dialog and chevrons visible. */
[data-testid="stDialog"] {z-index:9999 !important;}
[data-testid="stDialog"] [data-testid="stExpander"] {background:#11151d !important;border:1px solid #3b3f4d !important;}
[data-testid="stDialog"] [data-testid="stExpander"] summary,
[data-testid="stDialog"] [data-testid="stExpander"] button {color:#f5f7fa !important;}
[data-testid="stDialog"] [data-testid="stExpander"] svg,
[data-testid="stDialog"] [data-testid="stExpander"] svg path,
[data-testid="stDialog"] [data-testid="stExpander"] svg line,
[data-testid="stDialog"] [data-testid="stExpander"] svg polyline {color:#b8ff00 !important;stroke:#b8ff00 !important;fill:none !important;filter:drop-shadow(0 0 5px rgba(184,255,0,.75)) !important;}
[data-testid="stDialog"] button[aria-label="Close"] {color:#b8ff00 !important;opacity:1 !important;visibility:visible !important;}
[data-testid="stDialog"] button[aria-label="Close"] svg,
[data-testid="stDialog"] button[aria-label="Close"] svg path,
[data-testid="stDialog"] button[aria-label="Close"] svg line {color:#b8ff00 !important;stroke:#b8ff00 !important;opacity:1 !important;visibility:visible !important;}
button[key="sidebar_max"], button[key="dash_open_max"] {box-shadow:0 0 0 1px rgba(184,255,0,.45),0 0 14px rgba(184,255,0,.45) !important;}
[data-testid="stSidebar"] [data-testid="stToggle"] label {color:#b8ff00 !important;text-shadow:0 0 6px rgba(184,255,0,.55) !important;}
/* MAX popup: bright lime chevrons on dark controls. */
[data-testid="stExpander"] svg, [data-testid="stExpander"] button svg, [data-testid="stExpander"] svg path, [data-testid="stExpander"] svg line, [data-testid="stExpander"] svg polyline {color:#b8ff00 !important;stroke:#b8ff00 !important;fill:#b8ff00 !important;opacity:1 !important;filter:drop-shadow(0 0 5px rgba(184,255,0,.8)) !important;}
[data-testid="stExpander"] svg path, [data-testid="stExpander"] svg line, [data-testid="stExpander"] svg polyline {stroke:#b8ff00 !important;}

[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], [data-testid="stAppDeployButton"], footer {display:none !important;visibility:hidden !important;height:0 !important;min-height:0 !important;pointer-events:none !important;}
:root {--accent:#5b5ce2;--accent2:#4f46c5;--bg:#f6f7fb;--surface:#ffffff;--border:#e4e7ec;--text:#171a21;--muted:#687182;}
.block-container {padding-top:0!important;}\n .main-title {font-size:2.05rem;font-weight:900;color:#24124f;text-align:left;margin:18px 0 12px;letter-spacing:.01em;text-shadow:0 0 10px rgba(91,70,214,.18);}
.subtitle {text-align:center;color:#687182;margin:3px 0 18px;font-size:.92rem;}\n 
.stApp {background:#f6f7fb;}
section[data-testid="stSidebar"] {background:#ffffff;border-right:1px solid #e4e7ec;}
section[data-testid="stSidebar"] .stMetric {background:transparent;border:0;border-radius:0;padding:2px 4px;}
.sidebar-ai-agent {font-size:1.05rem;font-weight:850;letter-spacing:.02em;color:#a98cff;text-shadow:0 0 6px rgba(169,140,255,.85),0 0 14px rgba(137,125,255,.55);margin:0 0 6px 0;text-align:left;line-height:1.2;}\n .sidebar-max {padding:10px 12px 8px;border:1px solid #34304f;border-radius:14px;background:linear-gradient(135deg,#171c26,#211f35);margin:2px 0 8px;}
.sidebar-max-kicker {font-size:.62rem;letter-spacing:.12em;font-weight:800;color:#9b93ff;}
.sidebar-max-title {font-size:1.18rem;font-weight:850;color:#fff;margin-top:2px;}
.sidebar-max-text {font-size:.72rem;color:#aeb5c2;margin-top:2px;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:16px;}
.stButton > button {border-radius:11px;border:1px solid #303747;background:#171c26;color:#f5f7fa;font-weight:650;transition:.2s;}
.stButton > button:hover {border-color:var(--accent);color:#fff;box-shadow:0 0 0 1px rgba(137,125,255,.16);}
button[kind="primary"] {background:linear-gradient(135deg,#756be8,#897dff)!important;border:0!important;color:#fff!important;}
button[kind="primary"]:hover {filter:brightness(1.06);box-shadow:0 6px 22px rgba(137,125,255,.22);}
div[data-baseweb="tab-list"] {gap:5px;background:#ffffff!important;padding:5px;border-radius:14px;border:1px solid #e1e5eb;display:flex!important;visibility:visible!important;opacity:1!important;box-shadow:0 2px 10px rgba(20,25,40,.05);}
button[data-baseweb="tab"] {border-radius:10px;color:#252b3a!important;font-weight:800;visibility:visible!important;opacity:1!important;min-height:40px;background:#f4f5f8!important;}
button[data-baseweb="tab"] * {color:#252b3a!important;opacity:1!important;}
button[data-baseweb="tab"][aria-selected="true"] {background:linear-gradient(135deg,#eee9ff,#e5deff)!important;color:#4c1d95!important;box-shadow:0 0 0 1px rgba(91,70,214,.18),0 0 12px rgba(91,70,214,.14);}
button[data-baseweb="tab"][aria-selected="true"] * {color:#4c1d95!important;opacity:1!important;}
button[data-baseweb="tab"][aria-selected="true"] {background:#eef0ff;color:#4338ca!important;}
[data-testid="stFileUploader"] {border:1px dashed #b9c1ce;border-radius:14px;background:#f5f7fa;}
.stat-box {background:linear-gradient(135deg,#171c26 0%,#211f35 100%);border:1px solid #30364a;color:#f5f7fa;padding:20px;border-radius:16px;text-align:center;margin:5px;box-shadow:0 8px 24px rgba(0,0,0,.12);}
.stat-number {font-size:2.35rem;font-weight:900;margin:0;color:#f5f7fa;}
.stat-label {font-size:.9rem;color:#aeb5c2;margin:0;}
.section-kicker {font-size:.76rem;text-transform:uppercase;letter-spacing:.12em;color:#8f86f5;font-weight:800;margin-bottom:4px;}
.section-title {font-size:1.7rem;font-weight:800;margin-bottom:3px;color:#171a21;}
.section-subtitle {color:#687182;margin-bottom:18px;}
.pill {display:inline-block;padding:4px 10px;border-radius:999px;background:#eef0ff;color:#4338ca;border:1px solid #dfe2ff;font-size:.78rem;font-weight:650;}
[data-testid="stAlert"], div[data-baseweb="notification"] {background:#151922 !important;border:1px solid #303747 !important;color:#f5f7fa !important;border-radius:14px !important;}
/* ===== Responsive layout: desktop / tablet / phone ===== */
html, body { overflow-x:hidden !important; }
.mobile-nav-hint {display:none;color:#7a8494;font-size:.74rem;margin:4px 0 8px;}
.block-container { width:100% !important; max-width:1500px !important; margin:0 auto !important; padding-left:clamp(0.75rem,2.5vw,2.5rem) !important; padding-right:clamp(0.75rem,2.5vw,2.5rem) !important; }
[data-testid="stHorizontalBlock"] { width:100% !important; }
[data-testid="stTextInput"], [data-testid="stTextArea"], [data-testid="stSelectbox"], [data-testid="stNumberInput"], [data-testid="stDateInput"], [data-testid="stFileUploader"] { width:100% !important; }
.stButton > button, button[kind="primary"] { min-height:44px; }
@media (min-width: 769px) and (max-width: 1100px) {
    .block-container { padding-left:1rem !important; padding-right:1rem !important; }
    [data-testid="stHorizontalBlock"] { flex-wrap:wrap !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        flex:1 1 46% !important; min-width:46% !important; max-width:100% !important;
    }
    .main-title { font-size:2.05rem !important; }
    .section-title { font-size:1.45rem !important; }
    div[data-baseweb="tab-list"] { overflow-x:auto !important; flex-wrap:nowrap !important; }
    button[data-baseweb="tab"] { flex:0 0 auto !important; white-space:nowrap !important; }
}
@media (max-width: 768px) {
    .mobile-nav-hint {display:block;}
    .main-title {display:block !important; font-size:1.12rem !important; line-height:1.1 !important; margin:8px 0 7px !important; text-align:left !important; color:#24124f !important; text-shadow:0 0 9px rgba(91,70,214,.18) !important;}
    .block-container { padding:0.65rem 0.7rem 1.2rem !important; }
    .main-title { font-size:1.45rem !important; line-height:1.15 !important; margin:12px 0 10px !important; letter-spacing:.01em !important; }
    .subtitle { font-size:.78rem !important; margin-bottom:12px !important; }
    .section-title { font-size:1.28rem !important; line-height:1.2 !important; margin-top:4px !important; }
    .section-subtitle { font-size:.82rem !important; margin-bottom:12px !important; }
    .section-kicker { font-size:.65rem !important; }
    .stat-box { padding:12px 8px !important; margin:3px 0 !important; border-radius:12px !important; }
    .stat-number { font-size:1.55rem !important; }
    .stat-label { font-size:.72rem !important; }
    .stButton > button, button[kind="primary"] { min-height:46px !important; width:100% !important; }
    [data-testid="stHorizontalBlock"] { flex-direction:column !important; gap:.55rem !important; }
    [data-testid="stHorizontalBlock"] > [data-testid="column"] {
        width:100% !important; min-width:100% !important; max-width:100% !important; flex:1 1 100% !important;
    }
    div[data-baseweb="tab-list"] {
        position:sticky !important; top:0 !important; z-index:20 !important;
        overflow-x:auto !important; overflow-y:hidden !important;
        flex-wrap:nowrap !important; scrollbar-width:none !important;
        -webkit-overflow-scrolling:touch !important;
    }
    div[data-baseweb="tab-list"]::-webkit-scrollbar { display:none !important; }
    button[data-baseweb="tab"] {
        flex:0 0 auto !important; min-width:max-content !important;
        white-space:nowrap !important; padding:9px 11px !important;
        font-size:.78rem !important; color:#252b3a !important;
        background:#f4f5f8 !important; opacity:1 !important;
        border:1px solid #e1e4eb !important;
    }
    button[data-baseweb="tab"] * {color:#252b3a !important; opacity:1 !important;}    button[data-baseweb="tab"][aria-selected="true"] {
        color:#4c1d95 !important;
        background:linear-gradient(135deg,#eee9ff,#e5deff) !important;
        border-color:#c9bfff !important;
        box-shadow:0 0 10px rgba(91,70,214,.16) !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] * {color:#4c1d95 !important; opacity:1 !important;}
    section[data-testid="stSidebar"] { width:min(88vw,330px) !important; }
    section[data-testid="stSidebar"] .stButton > button { width:100% !important; }
    .sidebar-ai-agent { font-size:.95rem !important; }
    .sidebar-max { padding:9px 10px 7px !important; }
    .sidebar-max-title { font-size:1.05rem !important; }
    .sidebar-max-text { font-size:.68rem !important; }
    [data-testid="stFileUploader"] { padding:.25rem !important; }
    [data-testid="stMetric"] {padding:11px 9px !important; background:#ffffff !important; border:1px solid #ddd8f5 !important; border-radius:12px !important; box-shadow:0 4px 14px rgba(91,70,214,.08) !important;}
    [data-testid="stMetric"] [data-testid="stMetricValue"] {color:#21164d !important; font-weight:900 !important;}
    [data-testid="stMetric"] [data-testid="stMetricLabel"] {color:#596174 !important; font-weight:700 !important;}
    [data-testid="stMetric"] [data-testid="stMetricDelta"] {color:#5b4bd6 !important;}
    [data-testid="stExpander"] {border-radius:12px !important;}\n    [data-testid="stExpander"] svg, [data-testid="stExpander"] button svg, [data-testid="stExpander"] svg path, [data-testid="stExpander"] svg line, [data-testid="stExpander"] svg polyline {color:#b8ff00 !important;stroke:#b8ff00 !important;fill:#b8ff00 !important;opacity:1 !important;filter:drop-shadow(0 0 5px rgba(184,255,0,.8)) !important;}\n    [data-testid="stExpander"] svg path, [data-testid="stExpander"] svg line, [data-testid="stExpander"] svg polyline {stroke:#b8ff00 !important;}
    [data-baseweb="select"], [data-baseweb="input"], [data-testid="stTextArea"] {font-size:16px !important;}
    [data-testid="stDataFrame"], [data-testid="stTable"] { width:100% !important; overflow-x:auto !important; }
    .stMarkdown, .stCaption { overflow-wrap:anywhere !important; }
    [data-testid="stAlert"], div[data-baseweb="notification"] { font-size:.86rem !important; }
}

[data-testid="stAlert"] *, div[data-baseweb="notification"] * {color:#f5f7fa !important;}
/* ===== Readable light theme + controlled violet neon accents ===== */
[data-testid="stMetric"] {background:#ffffff !important;border:1px solid #ddd8f5 !important;border-radius:14px !important;box-shadow:0 4px 14px rgba(91,70,214,.08) !important;}
[data-testid="stMetric"] [data-testid="stMetricValue"] {color:#21164d !important;font-weight:900 !important;opacity:1 !important;}
[data-testid="stMetric"] [data-testid="stMetricLabel"] {color:#596174 !important;font-weight:700 !important;opacity:1 !important;}
[data-testid="stMetric"] [data-testid="stMetricDelta"] {color:#5b4bd6 !important;opacity:1 !important;}
.section-kicker {color:#6d4aff !important;text-shadow:0 0 7px rgba(109,74,255,.20);}
.section-title {color:#21164d !important;}
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {color:#21164d !important;}
[data-testid="stText"], [data-testid="stCaptionContainer"] {color:#596174 !important;}

[data-testid="stAlert"] svg, div[data-baseweb="notification"] svg {color:#897dff !important;}

/* UI chrome cleanup + MAX/sidebar recovery v7 */
/* Keep the real app sidebar available on desktop and mobile. */
aside[data-testid="stSidebar"], section[data-testid="stSidebar"], div[data-testid="stSidebar"] {
    display:block !important;
    visibility:visible !important;
    opacity:1 !important;
}
/* Hide only Streamlit/GitHub/platform chrome; do not hide app controls. */
a[href*="github.com"], a[href*="gitlab.com"], a[href*="bitbucket.org"],
a[aria-label*="GitHub" i], a[title*="GitHub" i],
a[aria-label*="Settings" i], a[title*="Settings" i] {
    display:none !important;
    visibility:hidden !important;
    pointer-events:none !important;
}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stAppDeployButton"], footer,
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"], [data-testid="stBottomBlock"],
div[data-testid="stBottom"] * , div[data-testid="stBottomBlockContainer"] * {

    display:none !important;
    visibility:hidden !important;
    height:0 !important;
    min-height:0 !important;
    pointer-events:none !important;
}
/* MAX dialog: restore visibility and make navigation arrows lime/neon. */
[data-testid="stDialog"], div[role="dialog"] {
    z-index:99999 !important;
    visibility:visible !important;
    opacity:1 !important;
}
[data-testid="stDialog"] [data-testid="stExpander"] button,
div[role="dialog"] [data-testid="stExpander"] button {
    color:#b8ff00 !important;
    opacity:1 !important;
    visibility:visible !important;
}
[data-testid="stDialog"] [data-testid="stExpander"] button svg,
[data-testid="stDialog"] [data-testid="stExpander"] button svg *,
[data-testid="stDialog"] [data-testid="stExpander"] svg,
[data-testid="stDialog"] [data-testid="stExpander"] svg *,
div[role="dialog"] [data-testid="stExpander"] button svg,
div[role="dialog"] [data-testid="stExpander"] button svg *,
div[role="dialog"] [data-testid="stExpander"] svg,
div[role="dialog"] [data-testid="stExpander"] svg * {
    color:#b8ff00 !important;
    stroke:#b8ff00 !important;
    fill:none !important;
    opacity:1 !important;
    visibility:visible !important;
    stroke-width:3px !important;
    filter:drop-shadow(0 0 6px rgba(184,255,0,.9)) !important;
}
[data-testid="stDialog"] [data-testid="stExpander"] button:hover,
div[role="dialog"] [data-testid="stExpander"] button:hover {
    color:#d6ff66 !important;
}
/* Keep the MAX launcher visually prominent. */
button[key="sidebar_max"], button[key="dash_open_max"] {
    background:linear-gradient(135deg,#7cff00,#b8ff00) !important;
    color:#101500 !important;
    border:1px solid #d7ff72 !important;
    box-shadow:0 0 0 1px rgba(184,255,0,.55),0 0 16px rgba(184,255,0,.55) !important;
    font-weight:900 !important;
}
/* Neon theme switch, without changing its behavior. */
[data-testid="stSidebar"] [data-testid="stToggle"] label,
[data-testid="stSidebar"] [data-baseweb="checkbox"] label {
    color:#b8ff00 !important;
    text-shadow:0 0 7px rgba(184,255,0,.65) !important;
}
</style>""",
    unsafe_allow_html=True,
)

st.markdown('<p class="main-title">AI AGENT CONTENT MANAGER</p><div class="mobile-nav-hint">Разделы · листайте меню влево и вправо</div>', unsafe_allow_html=True)


tab_dashboard, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
    [
        "⌂ Главная", "＋ Товар", "▦ Каталог", "✎ Тексты", "▶ Видео",
        "◷ План", "◉ Аналитика", "⚙ Настройки"
    ]
)

# ========== DASHBOARD ==========
with tab_dashboard:
    products = load_products()
    plan = load_plan()
    leads = load_leads()
    orders = load_orders()
    crm = crm_metrics(leads)
    om = order_metrics(orders, {"Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен"})
    cm = conversion_metrics(leads, orders)
    wm = workflow_metrics(plan)
    low = low_stock_products(products)
    due, overdue = [], []
    today = datetime.date.today()
    for item in plan:
        try:
            item_date = datetime.date.fromisoformat(str(item.get("date", "")))
            if item.get("status") != "Опубликовано":
                (overdue if item_date < today else due if item_date == today else []).append(item)
        except Exception:
            pass

    st.markdown('<div class="section-kicker">CONTROL CENTER</div><div class="section-title">Главная</div><div class="section-subtitle">Продажи, заявки, контент и остатки — в одном месте.</div>', unsafe_allow_html=True)

    d1, d2, d3, d4, d5 = st.columns(5)
    d1.metric("Продажи", f'{om["amount"]:,.0f} ₽'.replace(",", " "))
    d2.metric("Заявки", crm.get("total", 0))
    d3.metric("Заказы", om.get("total", 0))
    d4.metric("Конверсия", f'{cm["conversion"]:.1f}%')
    d5.metric("Товаров", len(products))

    st.markdown("---")
    left, right = st.columns(2)
    with left:
        st.markdown("### Контент и задачи")
        c1, c2, c3 = st.columns(3)
        c1.metric("В плане", wm.get("total", 0))
        c2.metric("На проверке", wm.get("counts", {}).get("На проверке", 0))
        c3.metric("Просрочено", wm.get("overdue", 0))
        if overdue:
            st.warning(f"Просроченных публикаций: {len(overdue)}")
        if due:
            st.info(f"На сегодня запланировано: {len(due)}")
        if not overdue and not due:
            st.success("Срочных контент-задач нет.")

    with right:
        st.markdown("### Склад")
        s1, s2 = st.columns(2)
        s1.metric("Позиций в каталоге", len(products))
        s2.metric("Низкий остаток", len(low))
        if low:
            for product, qty in low[:8]:
                st.write(f'• {max_product_title(product)} — {qty} шт.')
        else:
            st.success("Дефицитных позиций нет.")

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        st.markdown("### Продажи")
        st.write(f'Активных заказов: **{om["active"]}**')
        st.write(f'Завершённых заказов: **{om["completed"]}**')
        st.write(f'Отменённых заказов: **{om["cancelled"]}**')
        st.write(f'Сумма неотменённых заказов: **{om["amount"]:,.0f} ₽**'.replace(",", " "))
    with st.expander("🔗 Контент → продажи", expanded=True):
        attribution = load_attribution()
        st.caption("Новый слой атрибуции не меняет существующие заказы и CRM. Он готовит связь публикация → товар → лид → заказ.")
        if not attribution:
            st.info("Пока нет событий атрибуции. Существующий контент и продажи продолжают работать без изменений.")
        else:
            stats = attribution_metrics(attribution, leads, orders)
            if stats:
                for product_key, row in list(stats.items())[:8]:
                    st.write(f"• {product_key}: контента {row['content']}, заявок {row['leads']}, заказов {row['orders']}")

    with b:
        st.markdown("### Быстрые действия")
        if st.button("➕ Добавить товар", key="dash_add_product", use_container_width=True):
            st.info("Откройте раздел «Создать» — там можно сразу загрузить фото и создать карточку.")
        if st.button("📅 Открыть контент-план", key="dash_open_plan", use_container_width=True):
            st.info("Откройте раздел «План» для управления публикациями и workflow.")
        if st.button("⚡ Открыть MAX", key="dash_open_max", use_container_width=True):
            st.session_state["open_max"] = True
            st.rerun()

    st.markdown("---")
    st.markdown("### Состояние системы")
    checks = [
        ("Каталог", bool(products), f'{len(products)} товаров'),
        ("CRM", True, f'{len(leads)} заявок'),
        ("Заказы", True, f'{len(orders)} заказов'),
        ("Контент workflow", True, f'{len(plan)} материалов'),
        ("Склад", True, f'{len(low)} позиций с низким остатком'),
    ]
    for name, ok, detail in checks:
        st.write(("🟢" if ok else "🟡") + f" **{name}** — {detail}")

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
        file_name="ai_agent_content_manager_products_template.csv",
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
📹 Логотип AI Agent Content Manager
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
    st.markdown('<div class="section-kicker">CONTENT WORKFLOW</div><div class="section-title">Контент-центр</div><div class="section-subtitle">Единый процесс: идея → работа → проверка → готово → публикация.</div>', unsafe_allow_html=True)
    products = load_products()
    plan = load_plan()

    wm = workflow_metrics(plan)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Всего", wm["total"])
    m2.metric("В работе", wm["counts"].get("В работе", 0))
    m3.metric("На проверке", wm["counts"].get("На проверке", 0))
    m4.metric("Готово", wm["counts"].get("Готово", 0))
    m5.metric("Опубликовано", wm["counts"].get("Опубликовано", 0))
    if wm["overdue"]:
        st.warning(f"Просрочено: {wm['overdue']}")

    planner_tab, workflow_tab, adapt_tab, report_tab = st.tabs(["📅 План", "🔄 Workflow", "📣 Адаптация", "📊 Отчёт"])

    with planner_tab:
        if not products:
            st.info("Сначала создайте товар.")
        else:
            with st.form("plan_f", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    pd = st.date_input("Дата")
                    pl = st.selectbox("Платформа", PLATFORMS)
                with c2:
                    pn = [f"{p.get('brand','')} {p.get('name','')}".strip() for p in products]
                    sp = st.selectbox("Товар", pn)
                    ct = st.selectbox("Тип", CONTENT_TYPES)
                with c3:
                    sts = st.selectbox("Статус", STATUSES)
                    pr = st.selectbox("Приоритет", PRIORITIES)
                idea = st.text_area("Идея / текст")
                if st.form_submit_button("📌 Добавить в workflow"):
                    add_plan(ensure_workflow({"date": str(pd), "platform": pl, "product": sp,
                                              "type": ct, "idea": idea, "status": sts, "priority": pr}))
                    st.success("Материал добавлен.")
                    st.rerun()

            if plan:
                st.subheader("📅 Календарь по неделям")
                weeks = {}
                for i, raw_item in enumerate(plan):
                    item = ensure_workflow(raw_item)
                    try:
                        d = datetime.date.fromisoformat(str(item.get("date", "")))
                        wk = d.isocalendar()[1]
                    except Exception:
                        wk = 0
                    weeks.setdefault(wk, []).append((i, item))
                for wk in sorted(weeks.keys()):
                    with st.expander(f"Неделя {wk} · {len(weeks[wk])} материалов"):
                        for i, item in weeks[wk]:
                            st.write(f"**{item.get('date','')}** · {item.get('platform','')} · {item.get('type','')} · **{item.get('status','Идея')}**")
                            st.caption(f"{item.get('product','')} — {item.get('idea','')}")

            st.markdown("---")
            st.subheader("Управление материалами")
            for i, raw_item in enumerate(reversed(plan)):
                ri = len(plan) - 1 - i
                item = ensure_workflow(raw_item)
                with st.expander(f"{item.get('date','')} · {item.get('product','')} · {item.get('platform','')}"):
                    st.write(f"**Идея:** {item.get('idea','')}")
                    cs = item.get("status", "Идея")
                    ns = st.selectbox("Этап", STATUSES, index=STATUSES.index(cs) if cs in STATUSES else 0, key=f"st_{ri}")
                    if ns != cs:
                        updated = change_status(item, ns)
                        update_plan(ri, updated)
                        st.rerun()
                    st.caption(f"Приоритет: {item.get('priority','Обычный')}")
                    if item.get("history"):
                        st.caption("История изменений")
                        for h in item["history"][-5:]:
                            st.write(f"{h.get('time','')} · {h.get('from','')} → {h.get('to','')} · {h.get('actor','manager')}")
                    if st.button("🗑️ Удалить", key=f"dp_{ri}"):
                        delete_plan(ri)
                        st.rerun()

    with workflow_tab:
        st.subheader("🔄 Очередь на проверку")
        review_items = [(i, ensure_workflow(x)) for i, x in enumerate(plan) if ensure_workflow(x).get("status") == "На проверке"]
        if not review_items:
            st.info("Материалов на проверке пока нет.")
        else:
            for i, item in review_items:
                st.markdown(f"**{item.get('product','')} · {item.get('platform','')} · {item.get('type','')}**")
                st.write(item.get("idea", ""))
                a, b = st.columns(2)
                with a:
                    if st.button("✅ Утвердить", key=f"approve_{i}"):
                        update_plan(i, change_status(item, "Готово"))
                        st.rerun()
                with b:
                    if st.button("↩️ Вернуть в работу", key=f"return_{i}"):
                        update_plan(i, change_status(item, "В работе"))
                        st.rerun()
        st.markdown("---")
        st.subheader("🤖 AI-рекомендации")
        for rec in recommendations(products, plan):
            st.write(f"• {rec}")

    with adapt_tab:
        st.subheader("📣 Один материал → три канала")
        if not products:
            st.info("Сначала добавьте товары.")
        else:
            names = [f"{p.get('brand','')} {p.get('name','')}".strip() for p in products]
            sel = st.selectbox("Товар", names, key="content_adapt_product")
            p = products[names.index(sel)]
            base_item = {"product": sel, "type": "Пост", "status": "Идея"}
            adapted = adapt_content(base_item, p, {"Instagram": gen_instagram, "Telegram": gen_telegram, "VK": gen_vk})
            for channel in ["Instagram", "Telegram", "VK"]:
                st.markdown(f"**{channel}**")
                st.text_area(channel, adapted.get(channel, ""), height=150, key=f"adapt_{channel}")
            st.caption("Цены в карточки и тексты автоматически не добавляются.")

    with report_tab:
        st.subheader("📊 Отчёт и история")
        for line in report_lines(products, plan, load_leads(), load_orders()):
            st.write(line)
        report_text = "\n".join(report_lines(products, plan, load_leads(), load_orders()))
        st.download_button("⬇️ Скачать отчёт TXT", report_text, file_name=f"arsenal_content_report_{datetime.date.today()}.txt")
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["Дата","Платформа","Товар","Тип","Статус","Приоритет","Идея","История"])
        for item in plan:
            writer.writerow([item.get("date",""), item.get("platform",""), item.get("product",""),
                             item.get("type",""), item.get("status","Идея"), item.get("priority","Обычный"),
                             item.get("idea",""), json.dumps(item.get("history", []), ensure_ascii=False)])
        st.download_button("⬇️ Экспорт истории CSV", csv_buf.getvalue(),
                           file_name=f"arsenal_content_history_{datetime.date.today()}.csv", mime="text/csv")

# ========== 6: СТАТИСТИКА ==========
with tab6:
    st.markdown('<div class="section-kicker">GROWTH ENGINE</div><div class="section-title">Контент · Продажи · Аналитика · AI</div><div class="section-subtitle">Единый контур: товар → контент → публикация → заявка → заказ → выручка → следующая рекомендация.</div>', unsafe_allow_html=True)
    products = load_products()
    plan = load_plan()
    leads = load_leads()
    orders = load_orders()
    growth = ai_summary(products, leads, orders, plan)
    f = growth["funnel"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Контент", f["content"])
    c2.metric("Опубликовано", f["published"])
    c3.metric("Заявки", f["leads"])
    c4.metric("Заказы", f["orders"])
    c5.metric("Выручка", f"{f['revenue']:,.0f} ₽".replace(",", " "))

    st.markdown("---")
    a, b = st.columns(2)
    with a:
        st.subheader("Воронка")
        st.write(f"Контент: **{f['content']}**")
        st.write(f"Опубликовано: **{f['published']}**")
        st.write(f"Заявки: **{f['leads']}**")
        st.write(f"Заказы: **{f['orders']}**")
        st.write(f"Завершённые заказы: **{f['completed_orders']}**")
        st.write(f"Конверсия заявка → заказ: **{f['lead_to_order']:.1f}%**")
    with b:
        st.subheader("🤖 AI-рекомендации")
        for rec in growth["recommendations"]:
            st.write(f"• {rec}")

    st.markdown("---")
    st.subheader("🔗 Реальная атрибуция: публикация → заявка → заказ → выручка")
    attribution_rows = attribution_performance(plan, leads, orders)
    explicit = [x for x in attribution_rows if x["leads"] or x["orders"] or x["revenue"]]
    if explicit:
        st.caption("Показываются только явные связи по content_id. Это фактическая атрибуция события, а не вывод по совпадению названий.")
        for row in explicit[:20]:
            st.write(f"**{row['date']} · {row['channel']} · {row['format']}** · {row['product']} — заявки {row['leads']} · заказы {row['orders']} · {row['revenue']:,.0f} ₽".replace(",", " "))
    else:
        st.info("Явных связей пока нет. При создании заказа можно выбрать опубликованный материал — связь сохранится автоматически.")

    st.subheader("📦 Товары: связь контента и продаж")
    st.caption("Связь определяется по названию/артикулу товара в заявке, заказе и контент-плане; это атрибуция по совпадению, а не доказательство причинности.")
    for row in growth["products"][:20]:
        st.write(f"**{row['product']}** · контент {row['content']} · заявки {row['leads']} · заказы {row['orders']} · {row['revenue']:,.0f} ₽ · остаток {row['stock']} шт.".replace(",", " "))

    st.markdown("---")
    st.subheader("🚀 Следующий контент")
    for item in growth["next_content"]:
        st.write(f"• **{item['priority']}** · {item['type']} · {item['product']} — {item['idea']}")

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

# ==================== НАСТРОЙКИ МАГАЗИНА ====================
SETTINGS_FILE = Path("settings.json")
DEFAULT_SETTINGS = {
    "store_name": "AI Agent Content Manager",
    "city": "Краснодар",
    "delivery": "По России",
    "telegram": "",
    "vk": "",
    "instagram": "",
    "order_contact": "",
    "phone": "",
    "manager_name": "",
    "pickup_address": "",
    "payment_methods": "Наличные, перевод, карта",
    "return_policy": "Возврат и обмен — по действующим правилам магазина.",
    "delivery_methods": "Самовывоз, доставка по Краснодару, отправка по России",
    "delivery_terms": "",
    "content_signature": "AI Agent Content Manager — спортивная одежда, обувь и экипировка",
    "cta": "Напишите нам — поможем выбрать товар и оформить заказ.",
    "hashtags": "#ai_agent_content_manager #спорт #экипировка",
    "ai_seller_instructions": "Отвечай дружелюбно и по делу. Уточняй товар, размер и город. Не придумывай наличие, цену или характеристики.",
    "notification_contact": "",
    "card_template": "Dark Premium",
    "show_price_on_cards": "Нет",
    "main_sport": "Футбол",
    "ai_tone": "Дружелюбный и профессиональный",
    "ai_required_questions": "Товар, размер, город, способ получения",
    "ai_no_stock_reply": "Если товара нет, предложи похожие варианты из каталога.",
    "ai_escalation_reply": "Если вопрос нельзя решить по данным магазина, предложи связаться с менеджером.",
    "faq": [],
}

def load_settings():
    data = load_json(SETTINGS_FILE, {})
    result = DEFAULT_SETTINGS.copy()
    if isinstance(data, dict):
        result.update({k: data.get(k, "") for k in DEFAULT_SETTINGS})
    return result

def save_settings(data):
    save_json(SETTINGS_FILE, {k: str(data.get(k, "")).strip() for k in DEFAULT_SETTINGS})



# ========== 7: НАСТРОЙКИ ==========
with tab7:
    st.markdown('<div class="section-kicker">STORE SETTINGS</div><div class="section-title">Настройки магазина</div><div class="section-subtitle">Основная информация AI Agent Content Manager для контента и работы магазина.</div>', unsafe_allow_html=True)
    settings = load_settings()

    st.markdown("### 🏪 Магазин")
    s1, s2 = st.columns(2)
    with s1:
        store_name = st.text_input("Название магазина", value=settings["store_name"], key="settings_store_name")
        city = st.text_input("Город", value=settings["city"], key="settings_city")
        phone = st.text_input("Телефон", value=settings["phone"], key="settings_phone")
        manager_name = st.text_input("Имя менеджера", value=settings["manager_name"], key="settings_manager_name")
        pickup_address = st.text_input("Адрес самовывоза", value=settings["pickup_address"], key="settings_pickup_address")
    with s2:
        order_contact = st.text_input("Контакт для заказа", value=settings["order_contact"], key="settings_order_contact")
        telegram = st.text_input("Telegram", value=settings["telegram"], key="settings_telegram")
        vk = st.text_input("VK", value=settings["vk"], key="settings_vk")
        instagram = st.text_input("Instagram", value=settings["instagram"], key="settings_instagram")
        st.info("Логотип используется из файла logo.png в проекте.")

    st.markdown("### 📦 Заказы и доставка")
    o1, o2 = st.columns(2)
    with o1:
        payment_methods = st.text_input("Способы оплаты", value=settings["payment_methods"], key="settings_payment_methods")
        delivery_methods = st.text_input("Способы доставки", value=settings["delivery_methods"], key="settings_delivery_methods")
        delivery_terms = st.text_input("Сроки доставки", value=settings["delivery_terms"], key="settings_delivery_terms")
    with o2:
        delivery = st.text_input("Доставка", value=settings["delivery"], key="settings_delivery")
        return_policy = st.text_area("Возврат и обмен", value=settings["return_policy"], key="settings_return_policy")

    st.markdown("### ✍️ Контент")
    c1, c2 = st.columns(2)
    with c1:
        content_signature = st.text_input("Подпись магазина", value=settings["content_signature"], key="settings_content_signature")
        cta = st.text_input("Призыв к действию", value=settings["cta"], key="settings_cta")
        hashtags = st.text_input("Стандартные хэштеги", value=settings["hashtags"], key="settings_hashtags")
    with c2:
        main_sport = st.selectbox("Основной спорт", ["Футбол", "Баскетбол", "Все виды спорта"], index=["Футбол", "Баскетбол", "Все виды спорта"].index(settings["main_sport"]) if settings["main_sport"] in ["Футбол", "Баскетбол", "Все виды спорта"] else 0, key="settings_main_sport")
        card_template = st.selectbox("Шаблон карточки", list(TEMPLATES.keys()), index=list(TEMPLATES.keys()).index(settings["card_template"]) if settings["card_template"] in TEMPLATES else 0, key="settings_card_template")
        show_price_on_cards = st.selectbox("Показывать цену на карточках", ["Нет", "Да"], index=0 if settings["show_price_on_cards"] == "Нет" else 1, key="settings_show_price")

    st.markdown("### 🤖 AI-продавец")
    a1, a2 = st.columns(2)
    with a1:
        ai_tone = st.selectbox("Стиль общения", ["Дружелюбный и профессиональный", "Коротко и по делу", "Более продающий"], index=["Дружелюбный и профессиональный", "Коротко и по делу", "Более продающий"].index(settings["ai_tone"]) if settings["ai_tone"] in ["Дружелюбный и профессиональный", "Коротко и по делу", "Более продающий"] else 0, key="settings_ai_tone")
        ai_required_questions = st.text_input("Что обязательно уточнять", value=settings["ai_required_questions"], key="settings_ai_required")
        ai_no_stock_reply = st.text_area("Если товара нет", value=settings["ai_no_stock_reply"], height=80, key="settings_ai_no_stock")
    with a2:
        ai_escalation_reply = st.text_area("Если нужен менеджер", value=settings["ai_escalation_reply"], height=80, key="settings_ai_escalation")
        notification_contact = st.text_input("Куда отправлять уведомления о заявках", value=settings["notification_contact"], key="settings_notification_contact")
    ai_seller_instructions = st.text_area("Главная инструкция для AI-продавца", value=settings["ai_seller_instructions"], height=110, key="settings_ai_seller")

    st.markdown("### ❓ FAQ магазина")
    faq = settings.get("faq", [])
    faq_text = "\n".join(f"{item.get('question','')} | {item.get('answer','')}" for item in faq if isinstance(item, dict))
    faq_input = st.text_area("Вопрос | Ответ — по одному на строку", value=faq_text, height=180, key="settings_faq")
    st.caption("Пример: Как заказать? | Напишите название товара, размер и город.")

    if st.button("💾 Сохранить все настройки", type="primary", key="save_store_settings"):
        save_settings({
            "store_name": store_name,
            "city": city,
            "delivery": delivery,
            "telegram": telegram,
            "vk": vk,
            "instagram": instagram,
            "order_contact": order_contact,
            "phone": phone,
            "manager_name": manager_name,
            "pickup_address": pickup_address,
            "payment_methods": payment_methods,
            "return_policy": return_policy,
            "delivery_methods": delivery_methods,
            "delivery_terms": delivery_terms,
            "content_signature": content_signature,
            "cta": cta,
            "hashtags": hashtags,
            "ai_seller_instructions": ai_seller_instructions,
            "notification_contact": notification_contact,
            "card_template": card_template,
            "show_price_on_cards": show_price_on_cards,
            "main_sport": main_sport,
            "ai_tone": ai_tone,
            "ai_required_questions": ai_required_questions,
            "ai_no_stock_reply": ai_no_stock_reply,
            "ai_escalation_reply": ai_escalation_reply,
            "faq": [{"question": line.split("|",1)[0].strip(), "answer": line.split("|",1)[1].strip()} for line in faq_input.splitlines() if "|" in line and line.split("|",1)[0].strip() and line.split("|",1)[1].strip()],
        })
        st.success("Настройки сохранены.")
        st.rerun()


def ai_sales_reply(products, message):
    q = (message or "").strip()
    if not q:
        return "Напишите, что ищете — например: «бутсы 42 размера до 10000».", []
    found = product_search(products, q)
    lower = q.lower()
    if any(k in lower for k in ("достав", "оплат", "возврат", "налич", "размер")) and not found:
        return knowledge_answer(q), []
    if found:
        top = found[:5]        lines = ["Нашёл подходящие варианты:"]
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
    @st.dialog("⚡ AI Agent Content Manager MAX", width="large")
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
                    attribution_items = [x for x in load_plan() if x.get("status") == "Опубликовано" and x.get("content_id")]
                    content_choices = ["Не привязывать"] + [f'{x.get("date","")} · {x.get("platform","")} · {x.get("type","")} · {x.get("product","")}' for x in attribution_items[-50:]]
                    selected_content = st.selectbox("Контент / публикация", content_choices, key="max_order_content")
                if st.form_submit_button("➕ Создать заказ"):
                    content_id = ""
                    if selected_content != "Не привязывать":
                        idx = content_choices.index(selected_content) - 1
                        content_id = attribution_items[idx].get("content_id", "")
                    create_order(customer, contact, product_name, amount=amount, status=status, source=source, content_id=content_id)
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
            st.subheader("🚀 Центр автоматизации AI Agent Content Manager")
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
                            try:
                                source_img = Image.open(io.BytesIO(f.getvalue())).convert("RGB")
                                path = save_uploaded_photo(f, products_now[idx], idx)
                                products_now[idx]["original_image"] = path
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
                            except Exception as e:
                                skipped.append(f"{f.name}: ошибка обработки ({e})")
                                continue
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
                    generated = make_30_day_plan(products)                    existing = load_plan()
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
            st.subheader("Контент → продажи → AI")
            growth = ai_summary(products, leads, orders, plan)
            f = growth["funnel"]

            x, y, z, q = st.columns(4)
            x.metric("Заявки", f["leads"])
            y.metric("Заказы", f["orders"])
            z.metric("Конверсия", f"{f['lead_to_order']:.1f}%")
            q.metric("Выручка", f"{f['revenue']:,.0f} ₽".replace(",", " "))

            st.caption("Рекомендации строятся локально по данным магазина. При малом объёме данных система показывает направление для теста, а не выдаёт его за доказанный результат.")

            st.markdown("---")
            st.subheader("🤖 Что делать дальше")
            for rec in growth["recommendations"]:
                st.write(f"• {rec}")

            st.markdown("---")
            st.subheader("🎯 AI-фокус: товар · канал · формат")
            a1, a2, a3 = st.columns(3)
            with a1:
                st.markdown("**Товары**")
                for row in growth["products"][:5]:
                    st.write(f"**{row['product']}**")
                    st.caption(f"Сигнал {row['score']:.2f} · лиды {row['leads']} · заказы {row['orders']} · остаток {row['stock']}")
            with a2:
                st.markdown("**Каналы**")
                for row in growth["channels"]:
                    st.write(f"**{row['channel']}**")
                    st.caption(f"Сигнал {row['score']:.2f} · публикации {row['published']} · лиды {row['leads']} · заказы {row['orders']}")
            with a3:
                st.markdown("**Форматы**")
                for row in growth["formats"]:
                    st.write(f"**{row['format']}**")
                    st.caption(f"Сигнал {row['score']:.2f} · публикации {row['published']}")

            st.markdown("---")
            st.subheader("📝 Следующий контент")
            for item in growth["next_content"]:
                st.write(f"• **{item['type']} · {item['channel']}** · {item['product']}")
                st.caption(f"{item['idea']} {item['reason']}")

            st.caption(f"Режим AI: {growth.get('ai_mode', 'local_explainable')} · без платного API.")



        if st.button("Закрыть MAX", key="close_max"):
            st.session_state["open_max"] = False
            st.rerun()

    dialog()

if st.session_state.get("open_max", False):
    render_max()