    "card_template": "Dark Premium",
    "show_price_on_cards": "Нет",
    "main_sport": "Футбол",
    "ai_tone": "Дружелюбный и профессиональный",
    "ai_required_questions": "Товар, размер, город, способ получения",
    "ai_no_stock_reply": "Если товара нет, предложи похожие варианты из каталога.",
    "ai_escalation_reply": "Если вопрос нельзя решить по данным магазина, предложи связаться с менеджером.",
    "faq": [],
}

def load_settings():
    rows = data_load("settings", [])
    data = rows[0] if isinstance(rows, list) and rows and isinstance(rows[0], dict) else {}
    result = DEFAULT_SETTINGS.copy()
    result.update({k: data.get(k, DEFAULT_SETTINGS[k]) for k in DEFAULT_SETTINGS})
    if data.get("_saas_record_id"):
        result["_saas_record_id"] = data["_saas_record_id"]
    return result

def save_settings(data):
    payload = {k: data.get(k, "") for k in DEFAULT_SETTINGS}
    record_id = data.get("_saas_record_id")
    if record_id:
        payload["_saas_record_id"] = record_id
    data_save("settings", [payload])



# ========== 7: НАСТРОЙКИ ==========
with tab7: