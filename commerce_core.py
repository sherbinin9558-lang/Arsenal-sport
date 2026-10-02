"""Business logic for catalog, search, cart, orders and CRM.

No UI code lives here. The same services can be reused by Streamlit, Telegram,
Instagram integrations and a future API.
"""
from typing import Dict, List, Tuple
import re
from core_models import Product, Order, OrderItem, new_id, ORDER_STATUSES


def normalize_words(value: str) -> List[str]:
    return [w for w in re.findall(r"[a-zа-яё0-9-]+", (value or "").lower()) if len(w) > 1]


def product_search(products: List[Product], query: str) -> List[Tuple[float, Product]]:
    words = normalize_words(query)
    if not words:
        return [(0, p) for p in products if p.active]

    result = []
    for p in products:
        fields = {
            "name": p.name.lower(),
            "brand": p.brand.lower(),
            "article": p.article.lower(),
            "sport": p.sport.lower(),
            "category": p.category.lower(),
            "purpose": p.purpose.lower(),
            "color": p.color.lower(),
            "material": p.material.lower(),
            "surface": p.surface.lower(),
            "season": p.season.lower(),
            "level": p.level.lower(),
            "description": p.description.lower(),
            "specs": p.specs.lower(),
            "sizes": " ".join(p.sizes).lower(),
        }
        score = 0
        for word in words:
            if word in fields["name"]:
                score += 8
            elif word in fields["brand"]:
                score += 6
            elif word in fields["sport"] or word in fields["category"]:
                score += 5
            elif word in fields["purpose"] or word in fields["surface"]:
                score += 4
            elif any(word in value for value in fields.values()):
                score += 2
        if score:
            result.append((score, p))

    result.sort(key=lambda item: (-item[0], -item[1].total_stock, item[1].name))
    return result


def filter_products(
    products: List[Product],
    sport: str = "",
    category: str = "",
    brand: str = "",
    size: str = "",
    color: str = "",
    purpose: str = "",
    surface: str = "",
    only_available: bool = False,
) -> List[Product]:
    result = []
    for p in products:
        if sport and p.sport != sport:
            continue
        if category and p.category != category:
            continue
        if brand and p.brand != brand:
            continue
        if size and size not in p.sizes:
            continue
        if color and p.color != color:
            continue
        if purpose and p.purpose != purpose:
            continue
        if surface and p.surface != surface:
            continue
        if only_available and p.total_stock <= 0:
            continue
        result.append(p)
    return result


def cart_total(cart: List[OrderItem]) -> float:
    return sum(x.price * x.quantity for x in cart)


def create_order(
    customer_name: str,
    customer_contact: str,
    cart: List[OrderItem],
    source: str = "Сайт",
    comment: str = "",
) -> Order:
    if not cart:
        raise ValueError("Корзина пуста")
    if not customer_name.strip():
        raise ValueError("Не указано имя клиента")
    if not customer_contact.strip():
        raise ValueError("Не указан контакт клиента")

    return Order(
        id=new_id("ORD"),
        customer_name=customer_name.strip(),
        customer_contact=customer_contact.strip(),
        items=cart,
        source=source,
        comment=comment.strip(),
    )


def update_order_status(order: Order, status: str) -> Order:
    if status not in ORDER_STATUSES:
        raise ValueError("Недопустимый статус заказа")
    order.status = status
    return order


def inventory_summary(products: List[Product]) -> Dict:
    total_units = sum(p.total_stock for p in products)
    out_of_stock = sum(p.total_stock == 0 for p in products)
    low_stock = sum(0 < p.total_stock <= 3 for p in products)
    return {
        "products": len(products),
        "units": total_units,
        "out_of_stock": out_of_stock,
        "low_stock": low_stock,
        "available": len(products) - out_of_stock,
    }
