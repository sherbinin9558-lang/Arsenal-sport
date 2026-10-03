"""T-Bank payment-status webhook handler.

Deploy this module behind HTTPS (FastAPI/ASGI). It verifies the webhook
by querying T-Bank GetState instead of trusting the incoming status alone.
"""
from fastapi import FastAPI, Request, HTTPException
import os
from tbank_billing import get_state

app=FastAPI(title="Arsenal Sport Billing Webhook")

@app.post("/webhooks/tbank/payment-status")
async def payment_status(request: Request):
    body=await request.json()
    payment_id=body.get("PaymentId") or body.get("PaymentID")
    if not payment_id:
        raise HTTPException(status_code=400, detail="PaymentId is required")
    state=get_state(str(payment_id))
    status=state.get("Status")
    return {"ok":True,"payment_id":str(payment_id),"status":status}
