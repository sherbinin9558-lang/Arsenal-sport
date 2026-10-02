import streamlit as st
import json
from pathlib import Path
from core_models import ORDER_STATUSES
from commerce_core import filter_products, product_search, create_order, update_order_status, inventory_summary
from crm_core import load_leads, create_lead, update_lead, crm_metrics, STATUSES
from analytics_core import load_events, event_counts, track
from recommendation_core import recommend

PRODUCTS=Path("products.json")
CONFIG=Path("store_config.json")

def load_json(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default

st.set_page_config(page_title="Commerce OS",page_icon="◈",layout="wide")
cfg=load_json(CONFIG,{})
products=load_json(PRODUCTS,[])
leads=load_leads()
events=load_events()

st.markdown("""
<style>
.stApp{background:#0b0e13}.hero{padding:28px 32px;border:1px solid #292f3c;border-radius:22px;background:linear-gradient(135deg,#111722,#19152b);margin-bottom:18px}
.hero h1{font-size:2.4rem;margin:0}.hero p{color:#9da5b3}.kpi{padding:18px;border:1px solid #292f3c;border-radius:16px;background:#121720}
.kpi b{font-size:1.8rem}.muted{color:#8e97a6}
</style>
""",unsafe_allow_html=True)

st.markdown(f'<div class="hero"><h1>◈ {cfg.get("store_name","Store")} Commerce OS</h1><p>Единая система: каталог → остатки → поиск → заказ → CRM → аналитика → каналы</p></div>',unsafe_allow_html=True)

stock=inventory_summary(products)
cm=crm_metrics(leads)
cols=st.columns(5)
for c,label,val in zip(cols,["Товары","В наличии","Лиды","Новые лиды","Заказы"],[len(products),stock.get("available",0),cm["total"],cm["new"],cm["orders"]]):
    c.markdown(f'<div class="kpi"><span class="muted">{label}</span><br><b>{val}</b></div>',unsafe_allow_html=True)

tabs=st.tabs(["Обзор","Каталог","Поиск и AI","CRM","Заказы","Аналитика","Настройки"])

with tabs[0]:
    st.subheader("Панель управления")
    st.write("Режим:", cfg.get("mode","demo"))
    st.info("Сейчас используется демо-каталог. Реальные остатки можно импортировать позже, без ручного ввода сотен товаров.")
    st.subheader("Архитектура продукта")
    st.write("Каталог — единый источник данных. Все будущие Telegram, Instagram и сайт используют одно ядро.")

with tabs[1]:
    st.subheader("Каталог и остатки")
    sports=sorted({str(p.get("sport","")).strip() for p in products if p.get("sport")})
    cats=sorted({str(p.get("category","")).strip() for p in products if p.get("category")})
    brands=sorted({str(p.get("brand","")).strip() for p in products if p.get("brand")})
    a,b,c,d=st.columns(4)
    sport=a.selectbox("Спорт",["Все"]+sports)
    cat=b.selectbox("Категория",["Все"]+cats)
    brand=c.selectbox("Бренд",["Все"]+brands)
    available=d.checkbox("Только в наличии",value=False)
    fp=filter_products(products,sport=None if sport=="Все" else sport,category=None if cat=="Все" else cat,brand=None if brand=="Все" else brand,only_available=available)
    st.caption(f"Показано: {len(fp)}")
    for p in fp:
        with st.container(border=True):
            x,y=st.columns([3,2])
            with x:
                st.write(f"**{p.get('brand','')} {p.get('name','')}**")
                st.caption(f"Артикул: {p.get('article','—')} · {p.get('category','—')}")
                st.write(p.get("description","") or "Описание не заполнено")
            with y:
                sb=p.get("stock_by_size",{})
                st.write("**Остатки по размерам**")
                st.write(", ".join(f"{k}: {v}" for k,v in sb.items()) if sb else "Не загружены")
                st.caption("Цена хранится отдельно от рекламной карточки.")

with tabs[2]:
    st.subheader("Умный поиск и AI-рекомендации")
    q=st.text_input("Что ищет покупатель?",placeholder="Нужны бутсы 42 размера для искусственного поля")
    if q:
        track("search","dashboard",meta={"query":q})
        found=recommend(products,q)
        st.caption(f"Подобрано: {len(found)}")
        for i,p in enumerate(found,1):
            st.write(f"{i}. **{p.get('brand','')} {p.get('name','')}** · {p.get('category','—')} · {p.get('sizes','—')}")

with tabs[3]:
    st.subheader("CRM-лиды")
    with st.form("lead_form"):
        a,b=st.columns(2); name=a.text_input("Имя"); contact=b.text_input("Контакт")
        product=st.text_input("Интересующий товар"); message=st.text_area("Сообщение")
        if st.form_submit_button("Создать лид"):
            create_lead(name,contact,"Dashboard",message,product); st.success("Лид создан."); st.rerun()
    for lead in load_leads():
        with st.container(border=True):
            a,b,c=st.columns([3,2,1])
            a.write(f"**#{lead['id']} {lead.get('name','Без имени')}** — {lead.get('product','')}")
            a.caption(f"{lead.get('contact','')} · {lead.get('source','')}")
            ns=b.selectbox("Статус",STATUSES,index=STATUSES.index(lead.get("status")) if lead.get("status") in STATUSES else 0,key=f"lead_{lead['id']}")
            if ns!=lead.get("status"): update_lead(lead["id"],status=ns); st.rerun()
            c.write(lead.get("created_at",""))

with tabs[4]:
    st.subheader("Заказы")
    orders=load_json(Path("orders.json"),[])
    if not orders: st.info("Заказов пока нет.")
    for order in orders:
        with st.container(border=True):
            a,b,c=st.columns([3,2,1])
            a.write(f"**#{order.get('id','—')}** · {order.get('customer_name','')} · {order.get('customer_contact','')}")
            a.caption(order.get("comment",""))
            status=order.get("status","Новая")
            ns=b.selectbox("Статус",ORDER_STATUSES,index=ORDER_STATUSES.index(status) if status in ORDER_STATUSES else 0,key=f"ord_{order.get('id')}")
            if ns!=status: update_order_status(order["id"],ns); st.rerun()
            c.write(order.get("created_at",""))

with tabs[5]:
    st.subheader("Аналитика")
    counts=event_counts(load_events())
    if counts:
        for k,v in sorted(counts.items(),key=lambda x:-x[1]): st.write(f"**{k}:** {v}")
    else: st.info("События появятся после использования системы.")

with tabs[6]:
    st.subheader("Настройки магазина")
    st.write(f"**Название:** {cfg.get('store_name','Store')}")
    st.write(f"**Режим:** {cfg.get('mode','demo')}")
    st.write(f"**Основной канал:** {cfg.get('primary_channel','—')}")
    st.write("Telegram и Instagram подключаются к этому единому каталогу, а не создают отдельные каталоги.")
    st.download_button("Скачать конфигурацию",json.dumps(cfg,ensure_ascii=False,indent=2),file_name="store_config.json")

st.caption("Commerce OS · demo foundation")
