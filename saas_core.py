    with st.form("saas_onboarding_form"):
        business=st.selectbox("Что продаёте?",["Спортивный магазин","Одежда и обувь","Интернет-магазин","Другое"],key="onb_business")
        city=st.text_input("Город / регион",placeholder="Краснодарский край",key="onb_city")
        telegram=st.text_input("Telegram магазина",placeholder="@your_store",key="onb_telegram")
        instagram=st.text_input("Instagram",placeholder="@your_store",key="onb_instagram")
        shipping=st.selectbox("Доставка",["По России","По региону","Самовывоз","Другое"],key="onb_shipping")
        goal=st.selectbox("Главная цель",["Больше продаж","Больше заявок","Регулярный контент","Порядок в каталоге"],key="onb_goal")
        positioning=st.text_area("Чем магазин отличается?",placeholder="Например: большой выбор футбольной экипировки и быстрая доставка.",height=90,key="onb_positioning")
        submitted=st.form_submit_button("Сохранить и открыть MAX",type="primary",use_container_width=True)
    if submitted:
        try:
            onboarding_payload={"business_type":business,"city":city.strip(),"telegram":telegram.strip(),"instagram":instagram.strip(),"shipping":shipping,"goal":goal,"positioning":positioning.strip(),"onboarding_complete":True}
            existing=data_load("settings",[])
            if existing and isinstance(existing[0],dict) and existing[0].get("_saas_record_id"):
                onboarding_payload["_saas_record_id"]=existing[0]["_saas_record_id"]
            data_save("settings",[onboarding_payload])
            st.session_state["saas_onboarding_complete"]=True; st.success("Магазин настроен. MAX готов к работе."); st.rerun()
        except Exception as e: st.error(f"Не удалось сохранить настройки магазина: {e}")

def require_saas_access():