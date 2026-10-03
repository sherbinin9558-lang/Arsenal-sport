"""Content workflow helpers for Arsenal Sport AI Content Manager. Pure local functions; no external dependencies."""
from collections import Counter
import datetime
import hashlib

WORKFLOW_STATUSES = ["Идея", "В работе", "На проверке", "Готово", "Опубликовано"]
PLATFORM_ORDER = ["Instagram", "Telegram", "VK"]

def content_identity(item):
    stable_id = str(item.get("_saas_record_id") or item.get("content_id") or "").strip()
    if stable_id:
        return "cnt-" + hashlib.sha1(stable_id.encode("utf-8")).hexdigest()[:12]
    raw = "|".join(str(item.get(k, "")) for k in ("date", "platform", "product", "type", "idea"))
    return "cnt-" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

def ensure_workflow(item):
    item = dict(item or {})
    item.setdefault("content_id", content_identity(item))
    status = item.get("status", "Идея")
    if status not in WORKFLOW_STATUSES:
        status = "Идея"
    item["status"] = status
    item.setdefault("history", [])
    item.setdefault("created_at", str(datetime.datetime.now().isoformat(timespec="seconds")))
    return item

def change_status(item, status, actor="manager"):
    item = ensure_workflow(item)
    if status not in WORKFLOW_STATUSES:
        return item
    old = item.get("status", "Идея")
    if old != status:
        item["status"] = status
        if status == "Опубликовано":
            item.setdefault("publication_id", item.get("content_id"))
            item.setdefault("published_at", datetime.datetime.now().isoformat(timespec="minutes"))
        item["history"].append({
            "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "action": "status",
            "from": old,
            "to": status,
            "actor": actor,
        })
    return item

def adapt_content(item, product, generators):
    """Create channel-specific copy from the same content item."""
    result = dict(item or {})
    for platform in PLATFORM_ORDER:
        fn = generators.get(platform)
        if fn:
            result[platform] = fn(product, "Продающий")
    return result

def workflow_metrics(plan):
    counts = Counter(ensure_workflow(x).get("status", "Идея") for x in plan)
    overdue = 0
    today = datetime.date.today()
    for x in plan:
        try:
            d = datetime.date.fromisoformat(str(x.get("date", "")))
            if d < today and x.get("status") != "Опубликовано":
                overdue += 1
        except Exception:
            pass
    return {"total": len(plan), "counts": dict(counts), "overdue": overdue}

def recommendations(products, plan):
    metrics = workflow_metrics(plan)
    recs = []
    if not products:
        return ["Добавьте товары в каталог — контент-конвейер пока не из чего строить."]
    if not plan:
        recs.append("Создайте первый контент-план хотя бы на 7 дней.")
    if metrics["overdue"]:
        recs.append(f"Разберите {metrics['overdue']} просроченных публикаций.")
    for platform in PLATFORM_ORDER:
        n = sum(1 for x in plan if x.get("platform") == platform)
        if n == 0:
            recs.append(f"Добавьте контент для {platform}.")
    if metrics["counts"].get("Опубликовано", 0) == 0:
        recs.append("После проверки переведите готовые материалы в «Опубликовано», чтобы видеть историю.")
    if len(products) >= 10:
        recs.append("Используйте массовую генерацию для каталога и затем отправляйте лучшие материалы на проверку.")
    return recs[:6]

def report_lines(products, plan, leads=None, orders=None):
    m = workflow_metrics(plan)
    lines = [
        "ARSENAL SPORT — ОТЧЁТ ПО КОНТЕНТУ",
        f"Дата отчёта: {datetime.date.today().isoformat()}",
        f"Товаров в каталоге: {len(products)}",
        f"Материалов в плане: {m['total']}",
        f"Просрочено: {m['overdue']}",
    ]
    for status in WORKFLOW_STATUSES:
        lines.append(f"{status}: {m['counts'].get(status, 0)}")
    if leads is not None:
        lines.append(f"Заявок: {len(leads)}")
    if orders is not None:
        lines.append(f"Заказов: {len(orders)}")
    return lines
