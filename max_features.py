from datetime import date, timedelta
import re

KNOWLEDGE_BASE = {
    "доставка": "Доставка по России. Уточняйте город, способ и срок доставки у Arsenal Sport перед заказом.",
    "оплата": "Способ оплаты уточняется при оформлении заказа.",
    "размер": "Поможем подобрать размер по параметрам товара и данным клиента.",
    "возврат": "Условия возврата и обмена уточняются у магазина перед оформлением заказа.",
    "наличие": "Актуальное наличие нужно подтверждать перед заказом.",
}

def product_search(products, query):
    q = (query or "").strip().lower()
    if not q:
        return products
    words = [w for w in re.findall(r"[a-zа-яё0-9-]+", q) if len(w) > 1]
    scored = []
    for index, p in enumerate(products):
        hay = " ".join(str(p.get(k, "")) for k in ("name","brand","article","category","description","specs","sizes","color")).lower()
        score = sum(3 if w in str(p.get("name","")).lower() else 1 for w in words if w in hay)
        if score:
            scored.append((score, index, p))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [p for _, _, p in scored]

def catalog_metrics(products, plan):
    return {
        "products": len(products),
        "cards": sum(bool(p.get("card_image")) for p in products),
        "original_photos": sum(bool(p.get("original_image")) for p in products),
        "planned": len(plan),
        "published": sum(1 for x in plan if x.get("status") == "Опубликовано"),
        "in_work": sum(1 for x in plan if x.get("status") == "В работе"),
    }

def auto_content_bundle(product):
    name = product.get("name", "товар")
    brand = product.get("brand", "")
    category = product.get("category", "Другое")
    sizes = product.get("sizes", "уточняйте")
    color = product.get("color", "уточняйте")
    desc = product.get("description", "").strip()
    return {
        "instagram": f"🔥 {name} — новинка Arsenal Sport\n\n{desc}\n\nРазмеры: {sizes}\nЦвет: {color}\n\n📩 Напишите нам — поможем подобрать вариант.",
        "telegram": f"🏆 Arsenal Sport\n\n{name} {brand}\n{desc}\n\n📏 Размеры: {sizes}\n🎨 Цвет: {color}\n📩 Уточнить наличие и заказать можно в сообщениях.",
        "vk": f"{name} — {brand}\n\n{desc}\n\nРазмеры: {sizes} · Цвет: {color}\n\n#arsenal_sport #спорт",
        "reels_hook": f"«Ищете {category.lower()}? Покажу вариант: {name}.»",
        "stories": f"Опрос: «Как вам {name}?»\nВопрос: «Нужен размер {sizes}?»\nCTA: «Напишите Arsenal Sport»",
    }

def planner_suggestions(products, start=None):
    start = start or date.today()
    types = ["Пост", "Reels", "Stories", "Карусель"]
    platforms = ["Instagram", "Telegram", "VK"]
    result = []
    for i, p in enumerate(products[:7]):
        d = start + timedelta(days=i)
        result.append({
            "date": str(d),
            "platform": platforms[i % len(platforms)],
            "product": f"{p.get('brand','')} {p.get('name','')}".strip(),
            "type": types[i % len(types)],
            "idea": f"Показать {p.get('name','товар')} через пользу, детали и призыв написать в Arsenal Sport.",
            "status": "Идея",
            "priority": "Высокий" if i < 2 else "Обычный",
        })
    return result

def knowledge_answer(question):
    q = (question or "").lower()
    for key, answer in KNOWLEDGE_BASE.items():
        if key in q:
            return answer
    return "Уточните вопрос: доставка, оплата, размер, возврат или наличие."
