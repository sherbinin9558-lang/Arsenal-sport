"""Dashboard UI. Keeps dashboard rendering outside the application entrypoint."""
import datetime
import streamlit as st

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
    crm_metrics, order_metrics, conversion_metrics, workflow_metrics,
    low_stock_products, growth_recommendations, max_product_title,
    attribution_loader, attribution_metrics, add_product, add_plan,
    categories, can_write,
):
    _apply_client_first_layout()
    # Reuse the dashboard snapshot only until a successful write invalidates it.
    # This keeps the dashboard fast without showing stale data after edits.
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
    
    store_name = st.session_state.get("saas_tenant_name", "Ваш магазин")
    first_run = len(products) == 0 and len(leads) == 0 and len(orders) == 0
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
        d5.metric("Товаров", len(products))
    
        q1, q2, q3 = st.columns(3)
        with q1:
            st.markdown("### Следующий шаг")
            if ai_next:
                st.write(ai_next[0])
            else:
                st.write("MAX пока собирает данные.")
        with q2:
            st.markdown("### Сегодня")
            st.write(f"Контент: **{len(due)}** · Просрочено: **{len(overdue)}**")
            st.write(f"Активные заказы: **{om['active']}**")
        with q3:
            st.markdown("### Состояние")
            st.write(f"Каталог: **{len(products)}** товаров")
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
