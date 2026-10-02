"""Reusable domain models for the Arsenal Sport commerce core.

The models are intentionally store-agnostic so the application can later serve
multiple stores without changing the business logic.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
import uuid


ORDER_STATUSES = [
    "Новая",
    "Связались",
    "Ожидает оплаты",
    "Оплачен",
    "Собирается",
    "Отправлен",
    "Завершён",
    "Отменён",
]


@dataclass
class Product:
    id: str
    name: str
    brand: str = ""
    article: str = ""
    sport: str = ""
    category: str = ""
    purpose: str = ""
    sizes: List[str] = field(default_factory=list)
    stock_by_size: Dict[str, int] = field(default_factory=dict)
    color: str = ""
    material: str = ""
    surface: str = ""
    season: str = ""
    level: str = ""
    price: float = 0.0
    description: str = ""
    specs: str = ""
    image: str = ""
    active: bool = True

    @property
    def total_stock(self) -> int:
        return sum(max(0, int(v or 0)) for v in self.stock_by_size.values())

    @property
    def availability(self) -> str:
        if self.total_stock <= 0:
            return "Нет в наличии"
        if self.total_stock <= 3:
            return "Мало"
        return "В наличии"

    def to_dict(self):
        return asdict(self)


@dataclass
class OrderItem:
    product_id: str
    product_name: str
    size: str
    quantity: int
    price: float


@dataclass
class Order:
    id: str
    customer_name: str
    customer_contact: str
    items: List[OrderItem]
    status: str = "Новая"
    source: str = "Сайт"
    comment: str = ""
    lead_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    @property
    def total(self) -> float:
        return sum(x.price * x.quantity for x in self.items)

    def to_dict(self):
        data = asdict(self)
        data["total"] = self.total
        return data


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"
