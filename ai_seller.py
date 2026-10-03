"""AI seller conversation helpers.

Pure catalog/FAQ logic kept outside the Streamlit UI so MAX and the main app
can reuse the same implementation without importing each other.
"""

import re

from max_features import knowledge_answer, product_search


def ai_sales_reply(products, message):
    q = (message or "").strip()
    if not q:
        return "Напишите, что ищете — например: «бутсы 42 размера до 10000».", []

    found = product_search(products, q)
    lower = q.lower()

    if any(k in lower for k in ("достав", "оплат", "возврат", "налич", "размер")) and not found:
        return knowledge_answer(q), []

    if found:
        top = found[:5]
        lines = ["Нашёл подходящие варианты:"]
        for i, p in enumerate(top, 1):
            title = f"{p.get('brand','')} {p.get('name','')}".strip()
            details = []
            if p.get("sizes"):
                details.append(f"размеры: {p.get('sizes')}")
            if p.get("color"):
                details.append(f"цвет: {p.get('color')}")
            if p.get("article"):
                details.append(f"арт.: {p.get('article')}")
            lines.append(
                f"{i}. {title}" + (f" — {', '.join(details)}" if details else "")
            )
        lines.append("Выберите номер товара — помогу с деталями и следующим шагом.")
        return "\n".join(lines), top

    return (
        "Пока не нашёл точного совпадения. Напишите категорию, размер, "
        "цвет или бюджет — попробую подобрать из каталога."
    ), []


def sales_followup(products, message, current):
    q = (message or "").strip().lower()
    if not q:
        return "Напишите, что хотите уточнить.", current

    if current:
        nums = [int(x) for x in re.findall(r"\b([1-5])\b", q)]
        if nums:
            idx = nums[0] - 1
            if idx < len(current):
                p = current[idx]
                title = f"{p.get('brand','')} {p.get('name','')}".strip()
                return (
                    f"{title}. "
                    f"{p.get('description','Описание пока не заполнено.') or 'Описание пока не заполнено.'} "
                    f"Размеры: {p.get('sizes','уточняйте')}. "
                    f"Цвет: {p.get('color','уточняйте')}. "
                    f"Артикул: {p.get('article','уточняйте')}. "
                    "Наличие подтверждается перед заказом."
                ), [p]

    if any(k in q for k in ("достав", "оплат", "возврат", "налич", "размер")):
        return knowledge_answer(q), current

    found = product_search(products, q)
    if found:
        return ai_sales_reply(products, message)[0], found

    return (
        "Уточните размер, бюджет, цвет или вид товара — "
        "я попробую подобрать подходящий вариант."
    ), current
