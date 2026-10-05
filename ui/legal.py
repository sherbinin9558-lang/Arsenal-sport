from pathlib import Path
import json
import streamlit as st
from saas_core import export_current_tenant_data, request_account_deletion, current_role

DOCS = {
    "Политика конфиденциальности": "docs/legal/PRIVACY_POLICY.md",
    "Условия использования": "docs/legal/TERMS_OF_SERVICE.md",
    "Cookie Policy": "docs/legal/COOKIE_POLICY.md",
    "GDPR information": "docs/legal/GDPR_INFORMATION.md",
}

def render_legal():
    st.markdown(
        '<div class="section-kicker">LEGAL</div>'
        '<div class="section-title">Правовая информация</div>'
        '<div class="section-subtitle">Документы и требования к коммерческому запуску.</div>',
        unsafe_allow_html=True,
    )
    st.warning(
        "Документы на текущем этапе являются рабочими шаблонами. "
        "Перед коммерческим запуском необходимо заполнить реквизиты оператора, "
        "утвердить реальные сроки хранения и процессы удаления/экспорта и проверить тексты юристом."
    )
    st.markdown("### Ваши данные")
    st.caption("Экспорт включает только данные текущего магазина, доступные вашей учетной записи. Удаление запускается как запрос владельца и не выполняется автоматически.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Экспортировать мои данные", use_container_width=True, key="legal_export_data"):
            try:
                payload = export_current_tenant_data()
                raw = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
                st.download_button("Скачать JSON", data=raw.encode("utf-8"), file_name="ai_business_platform_data_export.json", mime="application/json", use_container_width=True, key="legal_download_export")
            except Exception as exc:
                st.error(f"Не удалось подготовить экспорт: {exc}")
    with col2:
        if current_role() == "owner":
            confirm = st.checkbox("Я понимаю, что запросит удаление данных магазина", key="legal_delete_confirm")
            if st.button("Запросить удаление данных", use_container_width=True, key="legal_delete_request", disabled=not confirm):
                try:
                    request_account_deletion("Запрос пользователя из раздела правовой информации.")
                    st.success("Запрос зарегистрирован. Фактическое удаление выполняется оператором после проверки и с учетом обязательных сроков хранения.")
                except Exception as exc:
                    st.error(f"Не удалось зарегистрировать запрос: {exc}")
        else:
            st.info("Запрос удаления доступен владельцу магазина.")

    for title, path in DOCS.items():
        with st.expander(title, expanded=False):
            file_path = Path(path)
            try:
                text = file_path.read_text(encoding="utf-8")
            except Exception as exc:
                st.error(f"Документ не удалось загрузить: {exc}")
                continue
            st.markdown(text)
