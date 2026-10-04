                activate_paid_subscription(plan,str(pid),None,provider="tbank",tenant=st.session_state.get("saas_tenant_id"))
                st.session_state["tbank_verified"]=True
                st.success(f"Оплата Т‑Банка подтверждена. Тариф {plan.upper()} активирован.")
            elif status:
                st.info(f"Статус платежа Т‑Банк: {status}.")
    elif (payment_id or checkout_id) and billing_return == "return" and not st.session_state.get("billing_verified"):
        from billing import get_checkout_by_order, get_payment
        if checkout_id:
            checkout=get_checkout_by_order(str(checkout_id), st.session_state.get("saas_tenant_id"))
            if not checkout or not checkout.get("provider_payment_id"):
                raise RuntimeError("Checkout-сессия не найдена или не содержит ID платежа.")
            payment_id=str(checkout["provider_payment_id"])
        payment=get_payment(payment_id)
        if payment.get("status") == "succeeded" and payment.get("paid"):
            plan=str((payment.get("metadata") or {}).get("plan") or st.session_state.get("billing_plan") or "").lower()
            tenant=str((payment.get("metadata") or {}).get("tenant_id") or st.session_state.get("saas_tenant_id") or "")
            if plan in ("starter","pro","business") and tenant == str(st.session_state.get("saas_tenant_id")):
                method_id=(payment.get("payment_method") or {}).get("id")
                activate_paid_subscription(plan,payment_id,method_id,provider="yookassa",tenant=tenant)
                st.session_state["billing_verified"]=True
                st.success(f"Оплата подтверждена. Тариф {plan.upper()} активирован.")
        elif payment.get("status") == "canceled":
            st.warning("Платёж отменён.")
except Exception as e:
    st.warning(f"Статус оплаты пока не подтверждён: {e}")


with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">'
        '<div class="sidebar-brand-kicker">AI AGENT</div>'