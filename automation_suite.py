"""Arsenal Sport free automation suite: bulk content, stock, photos and analytics."""
import re
from datetime import date, timedelta
from pathlib import Path
from saas_core import tenant_id

ASSET_ROOT = Path("tenant_assets")

def tenant_asset_dir() -> Path:
    # Never share uploaded media between tenants.
    return ASSET_ROOT / str(tenant_id())

def image_dir() -> Path:
    return tenant_asset_dir() / "product_images"

def card_dir() -> Path:
    return tenant_asset_dir() / "generated_cards"

def safe_slug(value):
    value = re.sub(r"[^a-zA-Zа-яА-ЯёЁ0-9_-]+", "_", str(value or "").strip())
    return value.strip("_")[:100] or "product"

def product_key(product, index=0):
    article = str(product.get("article", "")).strip()
    return article or safe_slug(f"{product.get('brand','')}_{product.get('name','')}") or f"product_{index+1}"

def ensure_dirs():
    image_dir().mkdir(parents=True, exist_ok=True)
    card_dir().mkdir(parents=True, exist_ok=True)

def stock_info(product):
    by_size = product.get("stock_by_size")
    if isinstance(by_size, dict) and by_size:
        total = 0
        clean = {}
        for size, value in by_size.items():
            try: qty = max(0, int(value or 0))
            except Exception: qty = 0
            clean[str(size)] = qty
            total += qty
        return total, clean, True
    raw = product.get("total_stock")
    if raw not in (None, ""):
        try: return max(0, int(raw)), {}, True
        except Exception: return None, {}, False
    return None, {}, False

def low_stock_products(products, threshold=2):
    result = []
    for p in products:
        qty, _, known = stock_info(p)
        if known and qty is not None and qty <= threshold:
            result.append((p, qty))
    return result

def content_for_product(product):
    name = str(product.get("name", "товар")).strip()
    brand = str(product.get("brand", "")).strip()
    desc = str(product.get("description", "")).strip()
    sizes = str(product.get("sizes", "уточняйте")).strip()
    color = str(product.get("color", "уточняйте")).strip()
    category = str(product.get("category", "спорттовар")).strip()
    title = f"{brand} {name}".strip()
    return {
        "Instagram": f"🔥 {title}\n\n{desc}\n\n📏 Размеры: {sizes}\n🎨 Цвет: {color}\n\n📩 Напишите в Arsenal Sport — поможем подобрать вариант.\n#arsenal_sport #спорт",
        "Telegram": f"🏆 Arsenal Sport\n\n{title}\n{desc}\n\n📏 Размеры: {sizes}\n🎨 Цвет: {color}\n📩 Уточнить наличие можно в сообщениях.",
        "VK": f"🔥 {title}\n\n{desc}\n\nРазмеры: {sizes} · Цвет: {color}\n\n📩 Напишите нам для заказа.",
        "Reels": f"Хук: «Ищете {category.lower()}? Покажу вариант {title}.»\nКадры: товар → детали → польза → CTA «Напишите Arsenal Sport».",
        "Stories": f"1. {title}\n2. Покажите деталь товара\n3. Опрос: «Как вам вариант?»\n4. CTA: «Напишите Arsenal Sport».",
    }

def make_30_day_plan(products, start=None):
    if not products: return []
    start = start or date.today()
    types = ["Пост", "Reels", "Stories", "Карусель", "Пост", "Reels", "Stories"]
    platforms = ["Instagram", "Telegram", "VK", "Instagram", "Telegram", "VK", "Instagram"]
    result = []
    for i in range(30):
        p = products[i % len(products)]
        title = f"{p.get('brand','')} {p.get('name','')}".strip()
        result.append({
            "date": str(start + timedelta(days=i)), "platform": platforms[i % len(platforms)],
            "product": title, "type": types[i % len(types)],
            "idea": f"Показать {p.get('name','товар')}: польза, детали, кому подходит и CTA.",
            "status": "Идея", "priority": "Высокий" if i < 3 else "Обычный",
        })
    return result

def bulk_update(products, indexes, field, value):
    changed = 0
    for i in indexes:
        if 0 <= i < len(products):
            products[i][field] = value
            changed += 1
    return changed

def analytics(products, leads, orders, plan):
    by_category, by_source, by_product = {}, {}, {}
    for p in products:
        cat = p.get("category", "Другое")
        by_category[cat] = by_category.get(cat, 0) + 1
    for lead in leads:
        src = lead.get("source", "Другое")
        by_source[src] = by_source.get(src, 0) + 1
    for order in orders:
        name = order.get("product", "Товар") or "Товар"
        by_product[name] = by_product.get(name, 0) + 1
    return {
        "products": len(products), "leads": len(leads), "orders": len(orders),
        "plan": len(plan), "published": sum(1 for x in plan if x.get("status") == "Опубликовано"),
        "categories": sorted(by_category.items(), key=lambda x: -x[1]),
        "sources": sorted(by_source.items(), key=lambda x: -x[1]),
        "top_products": sorted(by_product.items(), key=lambda x: -x[1])[:10],
    }

def save_uploaded_photo(uploaded_file, product, index=0):
    ensure_dirs()
    ext = Path(uploaded_file.name or "").suffix.lower() or ".jpg"
    path = image_dir() / f"{safe_slug(product_key(product,index))}{ext}"
    path.write_bytes(uploaded_file.getvalue())
    return str(path)
