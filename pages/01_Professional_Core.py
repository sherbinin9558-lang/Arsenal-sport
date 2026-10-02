import streamlit as st
import json
from pathlib import Path

from core_models import Product, OrderItem, ORDER_STATUSES, new_id
from commerce_core import product_search, filter_products, inventory_summary, create_order, stock_label

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
:root { --accent:#897dff; --panel:#151922; --panel2:#1b202c; --line:#2a3040; --muted:#9ca5b5; }
.block-container { max-width: 1500px; padding-top: 1.5rem; padding-bottom: 3rem; }
.hero { padding: 30px 34px; border-radius: 24px; margin-bottom: 20px; background: radial-gradient(circle at 85% 20%, #3a315f 0, #24203b 28%, #11151d 70%); border:1px solid #34304f; color:#fff; box-shadow:0 16px 45px rgba(0,0,0,.18); }
.hero h1 { margin:0; font-size:2.45rem; letter-spacing:.01em; }
.hero p { color:#b9c0cd; margin:.5rem 0 0; font-size:1rem; }
.badge { display:inline-block; padding:5px 10px; border-radius:999px; background:#2a2543; color:#c9c3ff; font-size:.78rem; margin-bottom:10px; }
.kpi { padding:17px 18px; border-radius:17px; background:linear-gradient(180deg,var(--panel2),var(--panel)); border:1px solid var(--line); min-height:104px; }
.kpi .n { font-size:1.75rem; font-weight:850; color:#fff; }
.kpi .l { color:var(--muted); font-size:.82rem; margin-top:3px; }
.section-note { color:var(--muted); font-size:.88rem; margin-bottom:12px; }
.product-name { font-size:1.05rem; font-weight:750; }
.stock-ok { color:#78d6a0; font-weight:700; }
.stock-low { color:#f2c36b; font-weight:700; }
.stock-none { color:#ee8d8d; font-weight:700; }
.meta { color:#9ca5b5; font-size:.86rem; }
</style>
""", unsafe_allow_html=True)

products = load_products()
summary = inventory_summary(products)
orders = load_json(ORDERS_FILE, [])

st.markdown(
    '<div class="hero"><div class="badge">PROFESSIONAL COMMERCE CORE</div>'
    '<h1>🏆 Arsenal Sport</h1>'
    '<p>Каталог · умный поиск · корзина · заказы · CRM — единая профессиональная система магазина.</p></div>',
    unsafe_allow_html=True,
)

kpis = [
    (summary["products"], "Товаров"),
    (summary["units"], "Единиц на остатке"),
    (summary["available"], "В наличии"),
    (summary["low_stock"], "Низкий остаток"),
    (len(orders), "Заказов"),
]
cols = st.columns(5)
for col, (value, label) in zip(cols, kpis):
    col.markdown(f'<div class="kpi"><div class="n">{value}</div><div class="l">{label}</div></div>', unsafe_allow_html=True)

st.divider()
tabs = st.tabs(["Каталог", "Умный поиск", "Корзина и заказ", "CRM"])

with tabs[0]:
    st.subheader("Каталог")
    st.markdown('<div class="section-note">Фильтруйте ассортимент так, как это делает современный интернет-магазин. Реальные остатки не подменяются демонстрационными данными.</div>', unsafe_allow_html=True)
    f1, f2, f3, f4, f5 = st.columns(5)
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
    with f5:
        only_available = st.checkbox("Только в наличии", value=False)

    filtered = filter_products(
        products,
        sport="" if sport == "Все" else sport,
        category="" if category == "Все" else category,
        brand="" if brand == "Все" else brand,
        size="" if size == "Все" else size,
        only_available=only_available,
    )
    st.caption(f"Показано: {len(filtered)} товаров")
    if filtered:
        available_count = sum(p.total_stock > 0 for p in filtered)
        low_count = sum(0 < p.total_stock <= 2 for p in filtered)
        m1, m2, m3 = st.columns(3)
        m1.metric("С подтверждённым остатком", available_count)
        m2.metric("Низкий остаток", low_count)
        m3.metric("Без остатка", len(filtered) - available_count)

    if not filtered:
        st.info("По выбранным фильтрам товары не найдены.")
    for p in filtered:
        with st.container(border=True):
            a, b, c = st.columns([4, 3, 2])
            with a:
                st.markdown(f'<div class="product-name">{p.name}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="meta">{p.brand} · Артикул {p.article or "—"}</div>', unsafe_allow_html=True)
                if p.description:
                    st.caption(p.description[:180] + ("…" if len(p.description) > 180 else ""))
            with b:
                st.write(f"**Спорт:** {p.sport or '—'}")
                st.write(f"**Категория:** {p.category or '—'}")
                details = [x for x in [p.color, p.material, p.surface, p.season] if x]
                if details:
                    st.caption(" · ".join(details))
            with c:
                status_class = "stock-ok" if p.total_stock > 3 else ("stock-low" if p.total_stock > 0 else "stock-none")
                st.markdown(f'<div class="{status_class}">{p.availability}</div>', unsafe_allow_html=True)
                if p.sizes:
                    stock_line = " · ".join(f"{s}: {p.stock_by_size.get(s, 0)}" for s in p.sizes)
                    st.caption(stock_line)
                    in_sizes = [s for s in p.sizes if p.stock_by_size.get(s, 0) > 0]
                    st.caption("Доступные размеры: " + (", ".join(in_sizes) if in_sizes else "нет подтверждённых"))
                st.write(stock_label(p))
                st.write(f"Цена: **{p.price:,.0f} ₽**" if p.price else "Цена пока не задана")

with tabs[1]:
    st.subheader("Умный поиск")
    st.markdown('<div class="section-note">Поиск учитывает название, бренд, спорт, категорию, назначение, поверхность, характеристики и размеры.</div>', unsafe_allow_html=True)
    query = st.text_input("Запрос клиента", placeholder="Например: бутсы Nike 42 для искусственного поля")
    if query:
        matches = product_search(products, query)
        st.caption(f"Найдено подходящих товаров: {len(matches)}")
        for score, p in matches[:10]:
            with st.container(border=True):
                left, right = st.columns([4, 1])
                with left:
                    st.markdown(f"**{p.name}** · {p.brand}")
                    st.write(f"{p.sport or 'спорт не задан'} · {p.category or 'категория не задана'} · {p.availability}")
                    if p.description:
                        st.caption(p.description[:160])
                with right:
                    st.metric("Релевантность", score)
                    st.caption("Размеры: " + (", ".join(p.sizes) or "—"))

with tabs[2]:
    st.subheader("Корзина и заявка")
    if "professional_cart" not in st.session_state:
        st.session_state.professional_cart = []

    available = [p for p in products if p.active and p.total_stock > 0]
    if not available:
        st.info("Подтверждённых остатков пока нет. В демо-режиме товары без stock_by_size намеренно считаются отсутствующими, чтобы система не обещала клиенту несуществующий товар.")
    else:
        selected = st.selectbox("Товар", range(len(available)), format_func=lambda i: f"{available[i].brand} {available[i].name}")
        p = available[selected]
        available_sizes = [s for s in p.sizes if p.stock_by_size.get(s, 0) > 0]
        size = st.selectbox("Размер", available_sizes) if available_sizes else None
        quantity = st.number_input("Количество", min_value=1, max_value=p.stock_by_size.get(size, 1) if size else 1, value=1)
        if st.button("Добавить в корзину", type="primary", use_container_width=True):
            st.session_state.professional_cart.append(OrderItem(p.id, p.name, size or "", int(quantity), p.price))
            st.success("Товар добавлен в корзину.")

    cart = st.session_state.professional_cart
    if cart:
        st.markdown("### Ваша корзина")
        total = 0
        for i, item in enumerate(cart):
            subtotal = item.price * item.quantity
            total += subtotal
            st.write(f"{i+1}. **{item.product_name}** · размер {item.size or '—'} · {item.quantity} шт. · {subtotal:,.0f} ₽")
        st.markdown(f"### Итого: {total:,.0f} ₽")
        name = st.text_input("Имя клиента")
        contact = st.text_input("Телефон / Telegram")
        comment = st.text_area("Комментарий к заказу")
        if st.button("Создать заказ", type="primary", use_container_width=True):
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
    status_counts = {status: 0 for status in ORDER_STATUSES}
    for order in orders:
        status_counts[order.get("status", "Новая")] = status_counts.get(order.get("status", "Новая"), 0) + 1
    sm = st.columns(4)
    for col, status in zip(sm, ORDER_STATUSES[:4]):
        col.metric(status, status_counts.get(status, 0))
    st.caption("Статус меняется вручную менеджером и сохраняется в orders.json. Остаток товара не списывается при создании заявки — это защищает от ложного списания до подтверждения заказа.")
    if not orders:
        st.info("Заказов пока нет. Первый заказ автоматически появится здесь.")
    else:
        for order in reversed(orders):
            with st.container(border=True):
                top = st.columns([2, 2, 2, 1.5])
                top[0].markdown(f"**{order.get('id', '—')}**")
                top[0].caption(order.get("created_at", ""))
                top[1].write(order.get("customer_name", "—"))
                top[1].caption(order.get("customer_contact", "—"))
                top[2].write(f"Сумма: {order.get('total', 0):,.0f} ₽")
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
                    st.caption(f"• {item.get('product_name', '')} · {item.get('size', '')} · {item.get('quantity', 0)} шт.")

st.caption("Arsenal Sport · Professional Core · store-agnostic foundation")
