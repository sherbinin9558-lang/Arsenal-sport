import json
import os
import re
import requests
from pathlib import Path

from max_features import product_search, knowledge_answer

PRODUCTS_FILE = Path("products.json")
TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
API = f"https://api.telegram.org/bot{TOKEN}" if TOKEN else ""

sessions = {}


def load_products():
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def tg(method, payload=None):
    r = requests.post(f"{API}/{method}", json=payload or {}, timeout=60)
    r.raise_for_status()
    return r.json()


def send(chat_id, text, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    return tg("sendMessage", payload)


def notify_admin(text):
    if ADMIN_CHAT_ID:
        try:
            send(ADMIN_CHAT_ID, text)
        except Exception:
            pass


def product_title(p):
    return f"{p.get('brand','')} {p.get('name','')}".strip()


def product_text(p):
    return (
        f"🏆 {product_title(p)}\n\n"
        f"{p.get('description','Описание пока не заполнено.')}\n\n"
        f"📏 Размеры: {p.get('sizes','уточняйте')}\n"
        f"🎨 Цвет: {p.get('color','уточняйте')}\n"
        f"🏷 Артикул: {p.get('article','уточняйте')}\n"
        f"⚙️ {p.get('specs','уточняются')}\n\n"
        "📦 Наличие подтверждается перед заказом."
    )


def order_keyboard(index):
    return [[
        {"text": "📦 Наличие", "callback_data": f"stock:{index}"},
        {"text": "🛒 Заказать", "callback_data": f"order:{index}"},
    ]]


def search_and_show(chat_id, query):
    products = load_products()
    found = product_search(products, query)
    sessions[chat_id] = found[:5]

    if not found:
        send(
            chat_id,
            "Пока не нашёл точного совпадения. Напишите категорию, размер, цвет или бюджет — попробую подобрать."
        )
        return

    lines = ["Нашёл подходящие варианты:"]
    keyboard = []
    for i, p in enumerate(found[:5], 1):
        details = []
        if p.get("sizes"):
            details.append(f"размеры: {p['sizes']}")
        if p.get("color"):
            details.append(f"цвет: {p['color']}")
        suffix = " · ".join(details)
        lines.append(f"{i}. {product_title(p)}" + (f" — {suffix}" if suffix else ""))
        keyboard.append([{"text": f"🔎 {i}. Подробнее", "callback_data": f"pick:{i-1}"}])

    lines.append("\nНапишите номер товара или нажмите кнопку.")
    send(chat_id, "\n".join(lines), keyboard)


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if not chat_id:
        return

    if text.startswith("/start"):
        sessions[chat_id] = []
        send(
            chat_id,
            "🏆 Добро пожаловать в Arsenal Sport!\n\n"
            "Я бесплатный AI-продавец магазина. Напишите, что ищете — "
            "например: «бутсы 42 размера для искусственного поля»."
        )
        return

    if text.startswith("/catalog"):
        send(chat_id, "Напишите категорию или товар: «футбол», «бутсы», «кроссовки», «форма», «мячи».")
        return

    current = sessions.get(chat_id, [])

    nums = re.findall(r"\b([1-5])\b", text.lower())
    if current and nums:
        idx = int(nums[0]) - 1
        if 0 <= idx < len(current):
            p = current[idx]
            sessions[chat_id] = [p]
            send(chat_id, product_text(p), order_keyboard(0))
            return

    lower = text.lower()
    if any(k in lower for k in ("достав", "оплат", "возврат")):
        send(chat_id, knowledge_answer(lower))
        return

    search_and_show(chat_id, text)


def handle_callback(callback):
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    data = callback.get("data", "")
    if not chat_id:
        return

    tg("answerCallbackQuery", {"callback_query_id": callback.get("id")})

    current = sessions.get(chat_id, [])
    if ":" not in data:
        return

    action, raw = data.split(":", 1)
    try:
        idx = int(raw)
    except ValueError:
        return

    if action == "pick" and 0 <= idx < len(current):
        p = current[idx]
        sessions[chat_id] = [p]
        send(chat_id, product_text(p), order_keyboard(0))
    elif action == "stock" and 0 <= idx < len(current):
        p = current[idx]
        send(chat_id, f"📦 По «{product_title(p)}» актуальное наличие подтверждается перед заказом.")
    elif action == "order" and 0 <= idx < len(current):
        p = current[idx]
        title = product_title(p)
        notify_admin(
            "🛒 Новый запрос на заказ Arsenal Sport\n\n"
            f"Товар: {title}\n"
            f"Артикул: {p.get('article','уточняется')}\n"
            f"Размеры: {p.get('sizes','уточняются')}\n"
            f"Клиент chat_id: {chat_id}"
        )
        send(
            chat_id,
            "🛒 Запрос передан менеджеру Arsenal Sport. "
            "Для оформления уточним размер и количество."
        )


def main():
    if not TOKEN:
        raise RuntimeError("Не задан TELEGRAM_TOKEN или TELEGRAM_BOT_TOKEN.")

    offset = None
    print("Arsenal Sport Telegram seller started.")

    while True:
        try:
            payload = {"timeout": 50}
            if offset is not None:
                payload["offset"] = offset
            result = tg("getUpdates", payload).get("result", [])

            for update in result:
                offset = update["update_id"] + 1
                if "callback_query" in update:
                    handle_callback(update["callback_query"])
                elif "message" in update:
                    handle_message(update["message"])
        except Exception as exc:
            print(f"Telegram polling error: {exc}")


if __name__ == "__main__":
    main()
