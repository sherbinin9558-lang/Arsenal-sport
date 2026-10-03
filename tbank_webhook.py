"""T-Bank payment-status webhook handler.

Deploy this module behind HTTPS (FastAPI/ASGI). It verifies the webhook
by querying T-Bank GetState instead of trusting the incoming status alone.
"""
from fastapi import FastAPI, Request, HTTPException\nfrom saas_core import activate_paid_subscription, SUPABASE_URL, tenant_id\nimport requests\nimport os
import os
from tbank_billing import get_state

app=FastAPI(title="Arsenal Sport Billing Webhook")

def _secret():
    try: return str(os.getenv("TBANK_WEBHOOK_SECRET") or "")
    except Exception: return ""

def _save_event(payment_id, status, tenant, plan):
    key=os.getenv("SUPABASE_SERVICE_ROLE_KEY","")
    if not key or not SUPABASE_URL: return
    h={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"return=minimal"}
    requests.post(f"{SUPABASE_URL}/rest/v1/billing_checkout_sessions",headers=h,json={"tenant_id":tenant,"provider":"tbank","provider_order_id":str(payment_id),"provider_payment_id":str(payment_id),"plan":plan,"status":str(status).lower()},timeout=15)

@app.post("/webhooks/tbank/payment-status")
async def payment_status(request: Request):
    auth=request.headers.get("authorization","")\n    expected=_secret()\n    if expected and auth != f"Bearer {expected}":\n        raise HTTPException(status_code=401, detail="Unauthorized")\n    body=await request.json()
    payment_id=body.get("PaymentId") or body.get("PaymentID")
    if not payment_id:
        raise HTTPException(status_code=400, detail="PaymentId is required")
    state=get_state(str(payment_id))
    status=state.get("Status")
    return {"ok":True,"payment_id":str(payment_id),"status":status}
