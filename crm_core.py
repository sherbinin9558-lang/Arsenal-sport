"""CRM workflow helpers shared by the UI and sales assistant."""
import json
from pathlib import Path
from datetime import datetime

LEADS_FILE = Path("leads.json")
STATUSES = ["Новый", "В работе", "Ожидает ответа", "Заказ оформлен", "Завершён", "Отменён"]

def load_leads():
    if not LEADS_FILE.exists():
        return []
    try:
        data = json.loads(LEADS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_leads(leads):
    LEADS_FILE.write_text(json.dumps(leads, ensure_ascii=False, indent=2), encoding="utf-8")

def create_lead(name="", contact="", source="Website", message="", product="", product_id=""):
    leads = load_leads()
    next_id = max([int(x.get("id", 0)) for x in leads if str(x.get("id", "")).isdigit()] or [0]) + 1
    lead = {
        "id": next_id, "name": name, "contact": contact, "source": source,
        "message": message, "product": product, "product_id": product_id,
        "status": "Новый", "created_at": datetime.now().isoformat(timespec="minutes")
    }
    leads.append(lead)
    save_leads(leads)
    return lead

def update_lead(lead_id, **changes):
    leads = load_leads()
    for lead in leads:
        if lead.get("id") == lead_id:
            lead.update(changes)
            lead["updated_at"] = datetime.now().isoformat(timespec="minutes")
            save_leads(leads)
            return lead
    return None

def convert_lead_to_order(lead_id, order_id):
    return update_lead(lead_id, status="Заказ оформлен", order_id=order_id)

def crm_metrics(leads):
    return {
        "total": len(leads),
        "new": sum(x.get("status") == "Новый" for x in leads),
        "in_work": sum(x.get("status") == "В работе" for x in leads),
        "orders": sum(x.get("status") == "Заказ оформлен" for x in leads),
        "completed": sum(x.get("status") == "Завершён" for x in leads),
    }
