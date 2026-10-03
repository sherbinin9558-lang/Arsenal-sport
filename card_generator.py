from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

CARD_SIZE = (1080, 1350)
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

TEMPLATES = {
    "Dark Premium":       {"bg": (9,12,18), "text": (248,249,252), "sec": (148,157,175), "accent": (105,120,255)},
    "Sport Performance":  {"bg": (8,16,27), "text": (248,250,255), "sec": (160,181,207), "accent": (65,160,255)},
    "Editorial Sport":    {"bg": (244,246,249), "text": (20,24,32), "sec": (91,99,113), "accent": (35,71,150)},
    "Black & Electric":   {"bg": (4,5,8), "text": (250,250,252), "sec": (135,140,151), "accent": (168,92,255)},
    "Спортивный":         {"bg": (18,25,36), "text": (245,247,250), "sec": (166,181,201), "accent": (105,164,235)},
    "Премиум":            {"bg": (18,20,27), "text": (239,242,247), "sec": (177,184,198), "accent": (137,125,255)},
}


def get_font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)
    except Exception:
        return ImageFont.load_default()

def fit_font(draw, text, max_w, max_size=80, min_size=38):
    for size in range(max_size, min_size - 1, -2):
        font = get_font(size, True)
        if draw.textbbox((0, 0), text, font=font)[2] <= max_w:
            return font
    return get_font(min_size, True)

def draw_centered(draw, text, font, fill, y, w):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (w - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)

def _fit_text_lines(draw, text, font, max_w, max_lines=2):
    words = str(text or "").split()
    if not words:
        return []
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_w:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    remainder = " ".join(words[len(lines):])
    if remainder:
        last = lines[-1]
        while remainder and draw.textbbox((0, 0), last + " …", font=font)[2] > max_w:
            parts = last.split()
            if len(parts) <= 1:
                break
            remainder = parts[-1] + " " + remainder
            last = " ".join(parts[:-1])
        lines[-1] = (last + " …").strip()
    return lines

def generate_card(image, name, brand, article, sizes, color, description, specs, category, template, logo_image=None):
    # Единая профессиональная система AI Agent Content Manager с четырьмя визуальными направлениями.
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
    logo_img = logo_image.convert("RGBA") if logo_image is not None else None
    logo_w = 235 if light else 255
    if logo_img:
        ratio = logo_w / max(1, logo_img.width)
        lr = logo_img.resize((logo_w, int(logo_img.height * ratio)), Image.Resampling.LANCZOS)
        canvas.paste(lr, (60, 48), lr)
    else:
        draw.text((60, 55), "AI AGENT CONTENT MANAGER", font=get_font(36, True), fill=t["text"])

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

    brand_text = (brand or "AI AGENT CONTENT MANAGER").upper()
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

    draw.text((W-310, H-108), "AI AGENT CONTENT MANAGER", font=get_font(21, True), fill=accent)
    return canvas

