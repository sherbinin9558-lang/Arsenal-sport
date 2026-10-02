import streamlit as st
import json
from pathlib import Path

from core_models import Product, OrderItem, ORDER_STATUSES, new_id
from commerce_core import (
    product_search,
    filter_products,
    inventory_summary,
    create_order,
)

PRODUCTS_FILE = Path("products.json")
ORDERS_FILE = Path("orders.json")


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_sizes(value):
    if isinstance(value, list):
        return [str(x) for x in value]
    raw = str(value or "").replace("–", "-").replace("—", "-")
    if "-" in raw and all(x.strip().isdigit() for x in raw.split("-", 1)):
        a, b = [int(x.strip()) for x in raw.split("-", 1)]
        return [str(x) for x in range(a, b + 1)]
    return [x.strip() for x in raw.split(",") if x.strip()]


def load_products():
    raw = load_json(PRODUCTS_FILE, [])
    result = []
    for item in raw:
        sizes = parse_sizes(item.get("sizes", ""))
        stock = item.get("stock_by_size", {})
        if not stock:
            # Demonstration data gets a safe, explicit inventory state instead
            # of pretending that every listed size is actually in stock.
            stock = {size: 0 for size in sizes}
        result.append(Product(
            id=str(item.get("id") or item.get("article") or new_id("PRD")),
            name=item.get("name", ""),
            brand=item.get("brand", ""),
            article=item.get("article", ""),
            sport=item.get("sport", ""),
            category=item.get("category", ""),
            purpose=item.get("purpose", ""),
            sizes=sizes,
            stock_by_size={str(k): int(v or 0) for k, v in stock.items()},
            color=item.get("color", ""),
            material=item.get("material", ""),
            surface=item.get("surface", ""),
            season=item.get("season", ""),
            level=item.get("level", ""),
            price=float(item.get("price", 0) or 0),
            description=item.get("description", ""),
            specs=item.get("specs", ""),
            image=item.get("card_image") or item.get("original_image", ""),
            active=item.get("active", True),
        ))
    return result


def save_orders(orders):
    save_json(ORDERS_FILE, orders)


st.set_page_config(page_title="Arsenal Sport · Professional Core", page_icon="🏆", layout="wide")

st.markdown("""
<style>
:root { --accent:#897dff; }
.block-container { max-width: 1500px; padding-top: 2rem; }
.hero {
    padding: 28px 32px; border-radius: 22px; margin-bottom: 22px;
    background: linear-gradient(135deg,#11151d,#24203b);
    border: 1px solid #34304f; color: #fff;
}
.hero h1 { margin:0; font-size:2.35rem; letter-spacing:.02em; }
.hero p { color:#aeb5c2; margin:.45rem 0 0; font-size:1rem; }
.kpi {
    padding:18px; border-radius:16px; background:#151922;
    border:1px solid #2a3040; min-height:105px;
}
.kpi .n { font-size:1.8rem; font-weight:850; color:#fff; }
.kpi .l { color:#9ca5b5; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)

products = load_products()
summary = inventory_summary(products)
orders = load_json(ORDERS_FILE, [])

st.markdown(
    '<div class="hero"><h1>🏆 Arsenal Sport · Professional Core</h1>'
    '<p>Единое ядро каталога, продаж, заказов и CRM. Готово к подключению каналов продаж.</p></div>',
    unsafe_allow_html=True,
)

k1, k2, k3, k4, k5 = st.columns(5)
for col, value, label in [
    (k1, summary["products"], "Товаров"),
    (k2, summary["units"], "Единиц на остатке"),
    (k3, summary["available"], "Есть в каталоге"),
    (k4, summary["low_stock"], "Мало"),
    (k5, len(orders), "Заказов"),
]:
    col.markdown(f'<div class="kpi"><div class="n">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)

st.divider()

tabs = st.tabs(["Каталог", "Умный поиск", "Корзина и заказ", "CRM"])

with tabs[0]:
    st.subheader("Профессиональный каталог")
    f1, f2, f3, f4 = st.columns(4)
    sports = sorted({p.sport for p in products if p.sport})
    categories = sorted({p.category for p in products if p.category})
    brands = sorted({p.brand for p in products if p.brand})
    sizes = sorted({s for p in products for s in p.sizes})
    with f1:
        sport = st.selectbox("Вид спорта", ["Все"] + sports)
    with f2:
        category = st.selectbox("Категория", ["Все"] + categories)
    with f3:
        brand = st.selectbox("Бренд", ["Все"] + brands)
    with f4:
        size = st.selectbox("Размер", ["Все"] + sizes)

    only_available = st.checkbox("Только товары в наличии", value=False)

    filtered = filter_products(
        products,
        sport="" if sport == "Все" else sport,
        category="" if category == "Все" else category,
        brand="" if brand == "Все" else brand,
        size="" if size == "Все" else size,
        only_available=only_available,
    )

    st.caption(f"Показано товаров: {len(filtered)}")
    for p in filtered:
        with st.container(border=True):
            a, b, c, d = st.columns([3, 2, 2, 1])
            with a:
                st.markdown(f"**{p.name}**")
                st.caption(f"{p.brand} · {p.article}")
            with b:
                st.write(f"Спорт: {p.sport or '—'}")
                st.write(f"Категория: {p.category or '—'}")
            with c:
                st.write(f"Наличие: **{p.availability}**")
                st.write(" · ".join(f"{s}: {p.stock_by_size.get(s,0)}" for s in p.sizes) or "Размеры не заданы")
            with d:
                st.write(f"{p.price:,.0f} ₽" if p.price else "Цена не задана")

with tabs[1]:
    st.subheader("Умный поиск")
    query = st.text_input(
        "Что ищет клиент?",
        placeholder="Например: бутсы Nike 42 для искусственного поля",
    )
    if query:
        matches = product_search(products, query)
        st.caption(f"Найдено: {len(matches)}")
        for score, p in matches[:10]:
            with st.container(border=True):
                st.markdown(f"**{p.name}** · {p.brand}")
                st.write(
                    f"{p.sport or 'спорт не задан'} · {p.category or 'категория не задана'} · "
                    f"{p.availability}"
                )
                st.caption(f"Релевантность: {score} · Размеры: {', '.join(p.sizes) or '—'}")

with tabs[2]:
    st.subheader("Корзина и заявка")
    if "professional_cart" not in st.session_state:
        st.session_state.professional_cart = []

    available = [p for p in products if p.active and p.total_stock > 0]
    if not available:
        st.info("В каталоге пока нет подтверждённых остатков. Это нормально для демонстрационного режима: реальные остатки подключим позже.")
    else:
        selected = st.selectbox(
            "Товар",
            range(len(available)),
            format_func=lambda i: f"{available[i].brand} {available[i].name}",
        )
        p = available[selected]
        available_sizes = [s for s in p.sizes if p.stock_by_size.get(s, 0) > 0]
        if available_sizes:
            size = st.selectbox("Размер", available_sizes)
            quantity = st.number_input(
                "Количество",
                min_value=1,
                max_value=p.stock_by_size.get(size, 1),
                value=1,
            )
            if st.button("Добавить в корзину", type="primary"):
                st.session_state.professional_cart.append(
                    OrderItem(p.id, p.name, size, int(quantity), p.price)
                )
                st.success("Товар добавлен в корзину.")

    cart = st.session_state.professional_cart
    if cart:
        st.markdown("### Корзина")
        total = 0
        for i, item in enumerate(cart):
            subtotal = item.price * item.quantity
            total += subtotal
            st.write(f"{i+1}. {item.product_name} · {item.size} · {item.quantity} шт. · {subtotal:,.0f} ₽")
        st.markdown(f"**Итого: {total:,.0f} ₽**")

        name = st.text_input("Имя клиента")
        contact = st.text_input("Телефон / Telegram")
        comment = st.text_area("Комментарий")
        if st.button("Создать заказ", type="primary"):
            try:
                order = create_order(name, contact, cart, source="Professional Core", comment=comment)
                orders.append(order.to_dict())
                save_orders(orders)
                st.session_state.professional_cart = []
                st.success(f"Заказ {order.id} создан.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

with tabs[3]:
    st.subheader("CRM заказов")
    if not orders:
        st.info("Заказов пока нет.")
    else:
        for order in reversed(orders):
            with st.container(border=True):
                top = st.columns([2, 2, 2, 1])
                top[0].markdown(f"**{order.get('id','—')}**")
                top[0].caption(order.get("created_at",""))
                top[1].write(order.get("customer_name","—"))
                top[1].caption(order.get("customer_contact","—"))
                top[2].write(f"Сумма: {order.get('total',0):,.0f} ₽")
                current = order.get("status", "Новая")
                selected_status = top[3].selectbox(
                    "Статус",
                    ORDER_STATUSES,
                    index=ORDER_STATUSES.index(current) if current in ORDER_STATUSES else 0,
                    key=f"order_status_{order.get('id')}",
                )
                if selected_status != current:
                    order["status"] = selected_status
                    save_orders(orders)
                    st.rerun()

                for item in order.get("items", []):
                    st.caption(
                        f"• {item.get('product_name','')} · "
                        f"{item.get('size','')} · {item.get('quantity',0)} шт."
                    )

st.caption("Professional Core · store-agnostic foundation · v1.0")
