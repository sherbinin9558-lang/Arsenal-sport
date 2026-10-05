"""Dashboard UI. Keeps dashboard rendering outside the application entrypoint."""
import datetime
import streamlit as st
from saas_core import saas_enabled, data_load_keyset

def _apply_client_first_layout():
    """Tighten global layout without changing application behavior."""
    st.markdown(
        """
        <style>
        /* Client-first layout: reduce dead space and establish a clear top edge. */
        .block-container {
            padding-top: 1.05rem !important;
            padding-bottom: 2rem !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            padding-top: .85rem !important;
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: .75rem !important;
        }
        .main-title {
            margin-top: 4px !important;
            margin-bottom: 8px !important;
        }
        .dashboard-hero {
            margin-top: 0 !important;
        }
        .owner-guide-card {
            margin: 0 0 14px !important;
            padding: 15px 18px !important;
            border: 1px solid #e2e5ee !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #ffffff 0%, #f7f7ff 100%) !important;
            box-shadow: 0 6px 22px rgba(37, 31, 82, .05) !important;
        }
        .owner-guide-kicker { font-size: .68rem !important; font-weight: 900 !important; letter-spacing: .12em !important; color: #5b4bd6 !important; margin-bottom: 4px !important; }
        .owner-guide-title { font-size: 1rem !important; font-weight: 850 !important; color: #21164d !important; margin-bottom: 10px !important; }
        .owner-guide-grid { display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)) !important; gap: 8px !important; }
        .owner-guide-grid > div { padding: 9px 10px !important; border-radius: 11px !important; background: rgba(255,255,255,.78) !important; border: 1px solid #e8e9f1 !important; }
        .owner-guide-grid b { display: block !important; font-size: .76rem !important; color: #26203f !important; margin-bottom: 2px !important; }
        .owner-guide-grid span { display: block !important; font-size: .7rem !important; line-height: 1.35 !important; color: #6b7280 !important; }
        .owner-guide-note { margin-top: 9px !important; font-size: .72rem !important; line-height: 1.4 !important; color: #697386 !important; }
        /* Keep the main navigation close to the product heading. */
        div[data-baseweb="tab-list"] {
            margin-top: 0 !important;
            margin-bottom: 10px !important;
        }
        /* Dialog: content should start near the title, not deep below it. */
        div[data-testid="stDialog"] [role="dialog"] {
            padding-top: 10px !important;
        }
        div[data-testid="stDialog"] [role="dialog"] .block-container {
            padding-top: .25rem !important;
            padding-bottom: 1.25rem !important;
        }
        div[data-testid="stDialog"] [role="dialog"] .max-ai-plan {
            margin-top: 4px !important;
        }
        /* Sidebar hierarchy: brand -> MAX -> status, with no artificial air. */
        section[data-testid="stSidebar"] .sidebar-brand {
            margin-top: 0 !important;
            margin-bottom: 3px !important;
            padding-top: 0 !important;
        }
        section[data-testid="stSidebar"] .sidebar-max {
            margin-top: 0 !important;
            margin-bottom: 7px !important;
        }
        @media (max-width: 768px) {
            .block-container {
                padding-top: .55rem !important;
                padding-bottom: 1.25rem !important;
            }
            section[data-testid="stSidebar"] > div:first-child {
                padding-top: .55rem !important;
            }
            .main-title {
                margin-top: 2px !important;
                margin-bottom: 6px !important;
            }
            .owner-guide-card { margin-bottom: 10px !important; padding: 12px 13px !important; }
            .owner-guide-title { font-size: .92rem !important; margin-bottom: 8px !important; }
            .owner-guide-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; gap: 6px !important; }
            .owner-guide-grid > div { padding: 8px !important; }
            .owner-guide-grid span { font-size: .68rem !important; }
            .owner-guide-note { font-size: .69rem !important; margin-top: 8px !important; }
            div[data-baseweb="tab-list"] {
                margin-bottom: 7px !important;
            }
            div[data-testid="stDialog"] [role="dialog"] {
                padding-top: 6px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_dashboard(
    *,
    load_products, load_plan, load_leads, load_orders,
    dashboard_snapshot=None, crm_metrics=None, order_metrics=None, conversion_metrics=None, workflow_metrics=None,
    low_stock_products, growth_recommendations, max_product_title,
    attribution_loader, attribution_metrics, add_product, add_plan,
    categories, can_write,
):
    _apply_client_first_layout()
    # Production SaaS uses bounded DB aggregates instead of materializing the
    # tenant's entire catalog/CRM/order/content datasets in Python.
    if saas_enabled() and dashboard_snapshot:
        summary = dashboard_snapshot()
        p_summary = summary.get("products", {}) or {}
        l_summary = summary.get("leads", {}) or {}
        o_summary = summary.get("orders", {}) or {}
        c_summary = summary.get("content", {}) or {}
        products = data_load_keyset("products", page_size=100).get("rows", [])
        plan = data_load_keyset("content_plan", page_size=100).get("rows", [])
        leads = data_load_keyset("leads", page_size=100).get("rows", [])
        orders = data_load_keyset("orders", page_size=100).get("rows", [])
        products_total = int(p_summary.get("total", 0) or 0)
        crm = dict(crm_metrics(leads) or {})
        crm["total"] = int(l_summary.get("total", 0) or 0)
        om = dict(order_metrics(orders, {"Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен"}) or {})
        om.update({
            "total": int(o_summary.get("total", 0) or 0),
            "active": int(o_summary.get("active", 0) or 0),
            "completed": int(o_summary.get("completed", 0) or 0),
            "cancelled": int(o_summary.get("cancelled", 0) or 0),
            "amount": float(o_summary.get("amount", 0) or 0),
        })
        cm = conversion_metrics(leads, orders)
        wm = workflow_metrics(plan)
        low = []
        for row in summary.get("low_stock_products", []) or []:
            low.append((row, row.get("stock", 0)))
        due, overdue = [], []
        # The aggregate is authoritative for counts; bounded rows are used only
        # for optional examples/details shown in the dashboard.
        today = datetime.date.today()
        for item in plan:
            try:
                item_date = datetime.date.fromisoformat(str(item.get("date", "")))
                if item.get("status") != "Опубликовано":
                    if item_date < today:
                        overdue.append(item)
                    elif item_date == today:
                        due.append(item)
            except Exception:
                pass
        wm["total"] = int(c_summary.get("total", 0) or 0)
        wm["overdue"] = int(c_summary.get("overdue", 0) or 0)
        wm.setdefault("counts", {})["На проверке"] = int(c_summary.get("review", 0) or 0)
        low_count = int(p_summary.get("low_stock", 0) or 0)
        due_count = int(c_summary.get("due_today", 0) or 0)
        overdue_count = int(c_summary.get("overdue", 0) or 0)
    else:
        revision = st.session_state.get("_app_data_revision", 0)
        if (
            "max_data_snapshot" not in st.session_state
            or st.session_state.get("_max_data_snapshot_revision") != revision
        ):
            st.session_state["max_data_snapshot"] = {
                "products": load_products(),
                "plan": load_plan(),
                "leads": load_leads(),
                "orders": load_orders(),
            }
            st.session_state["_max_data_snapshot_revision"] = revision
        snap = st.session_state["max_data_snapshot"]
        products = snap["products"]
        plan = snap["plan"]
        leads = snap["leads"]
        orders = snap["orders"]
        products_total = len(products)
        crm = crm_metrics(leads)
        om = order_metrics(orders, {"Новая", "Связались", "Ожидает оплаты", "Оплачен", "Собирается", "Отправлен"})
        cm = conversion_metrics(leads, orders)
        wm = workflow_metrics(plan)
        low = low_stock_products(products)
        low_count = len(low)
        due, overdue = [], []
        due_count = len(due)
        overdue_count = len(overdue)
        today = datetime.date.today()
        for item in plan:
            try:
                item_date = datetime.date.fromisoformat(str(item.get("date", "")))
                if item.get("status") != "Опубликовано":
                    (overdue if item_date < today else due if item_date == today else []).append(item)
            except Exception:
                pass

    store_name = st.session_state.get("saas_tenant_name", "Ваш магазин")
    first_run = products_total == 0 and int(crm.get("total", 0) or 0) == 0 and int(om.get("total", 0) or 0) == 0
    try:
        ai_next = growth_recommendations(products, leads, orders, plan)
    except Exception:
        ai_next = []
    
    st.markdown(
        f'<div class="dashboard-hero">'
        f'<div class="dashboard-hero-kicker">AI BUSINESS COMMAND CENTER</div>'
        f'<div class="dashboard-hero-title">Добро пожаловать в {store_name}</div>'
        f'<div class="dashboard-hero-text">MAX смотрит на каталог, контент и продажи и помогает решить следующую задачу — без лишней рутины.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    
    st.markdown(
        '<div class="owner-guide-card">'
        '<div class="owner-guide-kicker">КАК РАБОТАЕТ ПЛАТФОРМА</div>'
        '<div class="owner-guide-title">Один рабочий центр вместо десятка разрозненных инструментов</div>'
        '<div class="owner-guide-grid">'
        '<div><b>1 · Каталог</b><span>Товары, остатки и карточки в одном месте.</span></div>'
        '<div><b>2 · Контент</b><span>Тексты, Reels и контент-план без ручной рутины.</span></div>'
        '<div><b>3 · Продажи</b><span>CRM, заявки и заказы связаны с магазином.</span></div>'
        '<div><b>4 · AI</b><span>MAX анализирует данные и предлагает следующий шаг.</span></div>'
        '</div>'
        '<div class="owner-guide-note">Вы управляете бизнесом, а платформа берёт на себя повторяющиеся операции и помогает принимать решения.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    
    if first_run:
        st.markdown(
            '<div class="first-run-card"><div class="first-run-kicker">ПЕРВЫЙ ЗАПУСК</div>'
            '<div class="first-run-title">Запустим магазин за несколько шагов</div>'
            '<div class="first-run-text">Добавьте первый товар — затем MAX поможет создать контент и подготовить следующий шаг.</div></div>',
            unsafe_allow_html=True,
        )
        fr1, fr2, fr3 = st.columns(3)
        fr1.metric("Шаг 1", "Магазин ✓")
        fr2.metric("Шаг 2", "Первый товар", "сейчас")
        fr3.metric("Шаг 3", "Первый контент", "после товара")
        if can_write:
            with st.expander("Добавить первый товар прямо сейчас", expanded=st.session_state.get("first_run_quick_add", True)):
                with st.form("first_run_product_form", clear_on_submit=True):
                    q1, q2 = st.columns(2)
                    with q1:
                        fr_name = st.text_input("Название товара", placeholder="Футбольная форма")
                        fr_brand = st.text_input("Бренд", placeholder="Nike")
                        fr_article = st.text_input("Артикул", placeholder="ART-001")
                    with q2:
                        fr_category = st.selectbox("Категория", categories)
                        fr_price = st.text_input("Цена, ₽", placeholder="4990")
                        fr_stock = st.number_input("Остаток", min_value=0, value=1, step=1)
                    fr_submit = st.form_submit_button("Создать товар и передать его MAX", type="primary", use_container_width=True)
                if fr_submit:
                    if not fr_name.strip():
                        st.error("Укажите название товара.")
                    else:
                        try:
                            add_product({
                                "name": fr_name.strip(), "brand": fr_brand.strip(), "article": fr_article.strip(),
                                "category": fr_category, "price": fr_price.strip(), "stock": int(fr_stock),
                                "sizes": "", "color": "", "description": "", "specs": "",
                                "card_image": "", "date_added": str(datetime.date.today())
                            })
                            st.success("Товар создан. MAX уже может использовать его для контента и рекомендаций.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Не удалось создать товар: {e}")
    else:
        d1, d2, d3, d4, d5 = st.columns(5)
        d1.metric("Продажи", f'{om["amount"]:,.0f} ₽'.replace(",", " "))
        d2.metric("Заявки", crm.get("total", 0))
        d3.metric("Заказы", om.get("total", 0))
        d4.metric("Конверсия", f'{cm["conversion"]:.1f}%')
        d5.metric("Товаров", products_total)
    
        q1, q2, q3 = st.columns(3)
        with q1:
            st.markdown("### Следующий шаг")
            if ai_next:
                st.write(ai_next[0])
            else:
                st.write("MAX пока собирает данные.")
        with q2:
            st.markdown("### Сегодня")
            st.write(f"Контент: **{due_count}** · Просрочено: **{overdue_count}**")
            st.write(f"Активные заказы: **{om['active']}**")
        with q3:
            st.markdown("### Состояние")
            st.write(f"Каталог: **{products_total}** товаров")
            st.write(f"Заявки: **{crm.get('total',0)}** · Заказы: **{om.get('total',0)}**")
    
    st.markdown("---")
    left, right = st.columns(2)
    with left:
        st.markdown("### Контент и задачи")
        c1, c2, c3 = st.columns(3)
        c1.metric("В плане", wm.get("total", 0))
        c2.metric("На проверке", wm.get("counts", {}).get("На проверке", 0))
        c3.metric("Просрочено", wm.get("overdue", 0))
        if overdue:
            st.warning(f"Просроченных публикаций: {overdue_count}")
        if due:
            st.info(f"На сегодня запланировано: {due_count}")
        if not overdue and not due:
            st.success("Срочных контент-задач нет.")
    
    with right:
        st.markdown("### Склад")
        s1, s2 = st.columns(2)
        s1.metric("Позиций в каталоге", products_total)
        s2.metric("Низкий остаток", low_count)
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
        attribution = attribution_loader()
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
            st.session_state["dashboard_quick_add"] = True
        if st.button("📅 Добавить материал в план", key="dash_open_plan", use_container_width=True):
            st.session_state["dashboard_quick_plan"] = True

        if st.session_state.get("dashboard_quick_add"):
            with st.form("dashboard_quick_add_form", clear_on_submit=True):
                st.caption("Быстрое добавление без перехода в другой раздел.")
                name = st.text_input("Название товара", key="dash_quick_name")
                brand = st.text_input("Бренд", key="dash_quick_brand")
                article = st.text_input("Артикул", key="dash_quick_article")
                category = st.selectbox("Категория", categories, key="dash_quick_category")
                price = st.text_input("Цена, ₽", key="dash_quick_price")
                stock = st.number_input("Остаток", min_value=0, value=0, step=1, key="dash_quick_stock")
                submitted = st.form_submit_button("Создать товар", type="primary", use_container_width=True)
            if submitted:
                if not can_write:
                    st.error("У вас нет прав на создание товара.")
                elif not name.strip() or not brand.strip():
                    st.error("Укажите название и бренд.")
                else:
                    try:
                        add_product({
                            "name": name.strip(), "brand": brand.strip(), "article": article.strip(),
                            "category": category, "price": price.strip(), "stock": int(stock),
                            "total_stock": int(stock), "sizes": "", "color": "",
                            "description": "", "specs": "", "card_image": "",
                            "date_added": str(datetime.date.today()),
                        })
                        st.session_state["dashboard_quick_add"] = False
                        st.success("Товар создан.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Не удалось создать товар: {e}")

        if st.session_state.get("dashboard_quick_plan"):
            with st.form("dashboard_quick_plan_form", clear_on_submit=True):
                st.caption("Быстрое добавление материала в контент-план.")
                plan_date = st.date_input("Дата", value=datetime.date.today(), key="dash_quick_plan_date")
                platform = st.selectbox("Платформа", ["Instagram", "Telegram", "VK", "Другое"], key="dash_quick_plan_platform")
                product = st.text_input("Товар", key="dash_quick_plan_product")
                content_type = st.selectbox("Тип", ["Пост", "Reels", "Stories", "Карусель"], key="dash_quick_plan_type")
                idea = st.text_area("Идея / текст", key="dash_quick_plan_idea")
                priority = st.selectbox("Приоритет", ["Обычный", "Высокий", "Срочно"], key="dash_quick_plan_priority")
                submitted = st.form_submit_button("Добавить в план", type="primary", use_container_width=True)
            if submitted:
                if not can_write:
                    st.error("У вас нет прав на изменение контент-плана.")
                elif not product.strip():
                    st.error("Укажите товар.")
                else:
                    try:
                        add_plan({
                            "date": str(plan_date), "platform": platform, "product": product.strip(),
                            "type": content_type, "idea": idea.strip(), "status": "Идея", "priority": priority,
                        })
                        st.session_state["dashboard_quick_plan"] = False
                        st.success("Материал добавлен в план.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Не удалось добавить материал: {e}")
    
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
