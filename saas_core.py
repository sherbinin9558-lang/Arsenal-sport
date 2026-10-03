"""SaaS foundation: Supabase Auth + multi-tenant Postgres via PostgREST."""

import hashlib, json, os
from typing import Optional
import requests
import streamlit as st

PLAN_LIMITS={"trial":{"products":100,"users":1},"starter":{"products":1000,"users":3},"pro":{"products":10000,"users":10},"business":{"products":100000,"users":50}}

def _cfg(name, default=""):
    try: value=st.secrets.get(name, os.getenv(name, default))
    except Exception: value=os.getenv(name, default)
    return str(value or "").strip()

SUPABASE_URL=_cfg("SUPABASE_URL").rstrip("/")
SUPABASE_ANON_KEY=_cfg("SUPABASE_ANON_KEY")

def saas_enabled(): return bool(SUPABASE_URL and SUPABASE_ANON_KEY)

def _headers(token=None):
    h={"apikey":SUPABASE_ANON_KEY,"Content-Type":"application/json"}
    if token: h["Authorization"]=f"Bearer {token}"
    return h

def _request(method,path,token=None,**kwargs):
    r=requests.request(method,f"{SUPABASE_URL}{path}",headers=_headers(token),timeout=20,**kwargs)
    try: data=r.json()
    except Exception: data={"message":r.text}
    if not r.ok:
        raise RuntimeError(data.get("msg") or data.get("message") or data.get("error_description") or str(data))
    return data

def sign_up(email,password,store_name):
    return _request("POST","/auth/v1/signup",json={"email":email,"password":password,"data":{"store_name":store_name}})

def sign_in(email,password):
    return _request("POST","/auth/v1/token?grant_type=password",json={"email":email,"password":password})

def get_user(token): return _request("GET","/auth/v1/user",token=token)

def sign_out(token):
    try: _request("POST","/auth/v1/logout",token=token)
    except Exception: pass

def _rest_get(path,token,params=None): return _request("GET",path,token=token,params=params or {})
def _rest_post(path,token,payload): return _request("POST",path,token=token,json=payload)
def _rest_delete(path,token,params=None): return _request("DELETE",path,token=token,params=params or {})

def current_tenant(token,user_id=None):
    uid=user_id or st.session_state.get("saas_user_id")
    if not uid: return None
    rows=_rest_get("/rest/v1/memberships",token,params={"select":"tenant_id,role,tenants(id,name,slug,plan,status)","user_id":f"eq.{uid}"})
    return rows[0].get("tenants") if rows else None

def subscription(token,tenant_id):
    rows=_rest_get("/rest/v1/subscriptions",token,params={"select":"*","tenant_id":f"eq.{tenant_id}","limit":"1"})
    return rows[0] if rows else None

def _set_identity(user,tenant):
    st.session_state["saas_user_id"]=user.get("id")
    st.session_state["saas_email"]=user.get("email","")
    st.session_state["saas_tenant_id"]=tenant.get("id")
    st.session_state["saas_tenant_name"]=tenant.get("name","Магазин")
    st.session_state["saas_plan"]=tenant.get("plan","trial")
    st.session_state["saas_tenant_status"]=tenant.get("status","active")

def login_ui():
    st.markdown("## ⚡ AI Agent Content Manager")
    st.caption("SaaS-платформа для управления магазином: каталог, контент, CRM, заказы и аналитика.")
    tab1,tab2=st.tabs(["Войти","Создать магазин"])
    with tab1:
        email=st.text_input("Email",key="saas_login_email")
        password=st.text_input("Пароль",type="password",key="saas_login_password")
        if st.button("Войти",type="primary",use_container_width=True,key="saas_login"):
            try:
                result=sign_in(email.strip(),password)
                token=result.get("access_token")
                user=result.get("user") or get_user(token)
                tenant=current_tenant(token,user.get("id"))
                if not tenant: raise RuntimeError("Магазин не найден. Проверьте SaaS SQL-схему.")
                st.session_state["saas_access_token"]=token
                _set_identity(user,tenant)
                st.rerun()
            except Exception as e: st.error(f"Не удалось войти: {e}")
    with tab2:
        store=st.text_input("Название магазина",key="saas_signup_store")
        email=st.text_input("Email владельца",key="saas_signup_email")
        password=st.text_input("Пароль",type="password",key="saas_signup_password")
        repeat=st.text_input("Повторите пароль",type="password",key="saas_signup_password2")
        if st.button("Создать магазин",type="primary",use_container_width=True,key="saas_signup"):
            if len(password)<8: st.error("Пароль должен содержать минимум 8 символов.")
            elif password!=repeat: st.error("Пароли не совпадают.")
            elif not store.strip() or not email.strip(): st.error("Укажите название магазина и email.")
            else:
                try:
                    result=sign_up(email.strip(),password,store.strip())
                    token=result.get("access_token")
                    if not token:
                        st.success("Аккаунт создан. Подтвердите email, затем войдите.")
                    else:
                        user=result.get("user") or get_user(token)
                        tenant=current_tenant(token,user.get("id"))
                        if tenant:
                            st.session_state["saas_access_token"]=token
                            _set_identity(user,tenant)
                            st.rerun()
                        else: st.success("Магазин создан. Войдите после подтверждения email.")
                except Exception as e: st.error(f"Не удалось создать магазин: {e}")

def usage_snapshot():
    products=len(data_load("products", []))
    leads=len(data_load("leads", []))
    orders=len(data_load("orders", []))
    content=len(data_load("content_plan", []))
    return {"products": products, "leads": leads, "orders": orders, "content": content}

def render_account_bar():
    with st.sidebar:
        st.markdown("---")
        st.caption(f"Магазин · {st.session_state.get('saas_tenant_name','')}")
        plan=str(st.session_state.get('saas_plan','trial')).lower()
        st.caption(f"Тариф · {plan.upper()}")
        if plan in PLAN_LIMITS:
            u=usage_snapshot()
            max_products=PLAN_LIMITS[plan]["products"]
            st.progress(min(1.0, u["products"]/max_products), text=f"Каталог · {u['products']} / {max_products}")
        if st.button("Выйти",key="saas_logout",use_container_width=True):
            token=st.session_state.get("saas_access_token")
            if token: sign_out(token)
            for k in list(st.session_state):
                if k.startswith("saas_"): del st.session_state[k]
            st.rerun()

def plan_catalog():
    return {
        "starter":{"name":"STARTER","products":1000,"users":3,"description":"Для небольшого магазина"},
        "pro":{"name":"PRO","products":10000,"users":10,"description":"Для растущего бизнеса"},
        "business":{"name":"BUSINESS","products":100000,"users":50,"description":"Для сети и большого каталога"},
    }

def subscription_snapshot():
    token=st.session_state.get("saas_access_token")
    tid=tenant_id()
    if not saas_enabled() or not token:
        return {"plan":tenant_plan(),"status":"trialing","provider":None,"current_period_end":None}
    try:
        row=subscription(token,tid) or {}
        return {
            "plan":row.get("plan",tenant_plan()),
            "status":row.get("status","trialing"),
            "provider":row.get("provider"),
            "current_period_end":row.get("current_period_end"),
        }
    except Exception:
        return {"plan":tenant_plan(),"status":"unknown","provider":None,"current_period_end":None}

def request_plan_change(plan):
    if plan not in ("starter","pro","business"):
        raise ValueError("Недопустимый тариф.")
    st.session_state["requested_plan"]=plan
    return True

def current_role(token=None):
    if not saas_enabled():
        return "owner"
    token=token or st.session_state.get("saas_access_token")
    uid=st.session_state.get("saas_user_id")
    tid=tenant_id()
    if not token or not uid or not tid:
        return "viewer"
    rows=_rest_get("/rest/v1/memberships",token,params={"select":"role","tenant_id":f"eq.{tid}","user_id":f"eq.{uid}","limit":"1"})
    return rows[0].get("role","viewer") if rows else "viewer"

def team_members():
    token=st.session_state.get("saas_access_token")
    if not saas_enabled() or not token:
        return [{"user_id":st.session_state.get("saas_user_id","demo-user"),"role":"owner"}]
    return _rest_get("/rest/v1/memberships",token,params={"select":"user_id,role,created_at","tenant_id":f"eq.{tenant_id()}","order":"created_at.asc"})

def team_invitations():
    token=st.session_state.get("saas_access_token")
    if not saas_enabled() or not token:
        return []
    return _rest_get("/rest/v1/invitations",token,params={"select":"id,email,role,status,created_at,expires_at","tenant_id":f"eq.{tenant_id()}","status":"eq.pending","order":"created_at.desc"})

def create_team_invitation(email,role):
    token=st.session_state.get("saas_access_token")
    if not saas_enabled() or not token:
        return None
    payload={"tenant_id":tenant_id(),"email":email.strip().lower(),"role":role,"invited_by":st.session_state.get("saas_user_id")}
    return _rest_post("/rest/v1/invitations",token,payload)

def onboarding_complete():
    if not saas_enabled():
        return True
    settings=data_load("settings", [])
    return bool(settings and isinstance(settings[0], dict) and settings[0].get("onboarding_complete"))

def render_onboarding():
    st.markdown("## 🚀 Настройка магазина")
    st.caption("Заполним основные данные один раз. Их можно изменить позже в настройках.")
    with st.form("saas_onboarding_form"):
        business=st.selectbox("Тип бизнеса", ["Спортивный магазин","Одежда и обувь","Интернет-магазин","Другое"], key="onb_business")
        city=st.text_input("Город / регион", key="onb_city")
        telegram=st.text_input("Telegram магазина", placeholder="@your_store", key="onb_telegram")
        instagram=st.text_input("Instagram", placeholder="@your_store", key="onb_instagram")
        shipping=st.selectbox("Доставка", ["По России","По региону","Самовывоз","Другое"], key="onb_shipping")
        submitted=st.form_submit_button("Сохранить и открыть платформу", type="primary", use_container_width=True)
    if submitted:
        data_save("settings", [{
            "business_type": business,
            "city": city.strip(),
            "telegram": telegram.strip(),
            "instagram": instagram.strip(),
            "shipping": shipping,
            "onboarding_complete": True
        }])
        st.session_state["saas_onboarding_complete"]=True
        st.rerun()

def require_saas_access():
    if not saas_enabled():
        if not st.session_state.get("saas_demo"):
            st.session_state["saas_demo"]=True
            demo={"id":"demo-user","email":"demo@example.com","tenant_id":"demo-tenant","tenant_name":"Demo Store","plan":"pro","status":"active"}
            _set_identity(demo,{"id":"demo-tenant","name":"Demo Store","plan":"pro","status":"active"})
        render_account_bar()
        return True
    token=st.session_state.get("saas_access_token")
    if not token:
        login_ui()
        return False
    try:
        user=get_user(token); tenant=current_tenant(token,user.get("id"))
        if not tenant: raise RuntimeError("Магазин не найден.")
        _set_identity(user,tenant)
        if not onboarding_complete() and not st.session_state.get("saas_onboarding_complete"):
            render_onboarding()
            return False
        render_account_bar(); return True
    except Exception:
        for k in list(st.session_state):
            if k.startswith("saas_"): del st.session_state[k]
        login_ui(); return False

def tenant_id(): return st.session_state.get("saas_tenant_id","demo-tenant")
def tenant_plan(): return st.session_state.get("saas_plan","trial")
def limit(name): return PLAN_LIMITS.get(tenant_plan(),PLAN_LIMITS["trial"]).get(name,0)
def feature_allowed(name,current_count=0):
    maximum=limit(name)
    return maximum<=0 or current_count<maximum

def data_load(entity,default):
    if not saas_enabled():
        path=f"data/{tenant_id()}_{entity}.json"
        try:
            with open(path,encoding="utf-8") as f: return json.load(f)
        except Exception:
            legacy={"products":"products.json","content_plan":"content_plan.json","content_attribution":"content_attribution.json","leads":"leads.json","orders":"orders.json"}.get(entity)
            if legacy:
                try:
                    with open(legacy,encoding="utf-8") as f: return json.load(f)
                except Exception: pass
            return default
    token=st.session_state.get("saas_access_token")
    rows=_rest_get("/rest/v1/app_data",token,params={"select":"record_id,payload","tenant_id":f"eq.{tenant_id()}","entity":f"eq.{entity}"})
    return [x.get("payload",{}) for x in rows] if rows else default

def data_save(entity,rows):
    rows=rows if isinstance(rows,list) else []
    if not saas_enabled():
        os.makedirs("data",exist_ok=True)
        with open(f"data/{tenant_id()}_{entity}.json","w",encoding="utf-8") as f: json.dump(rows,f,ensure_ascii=False,indent=2)
        return
    token=st.session_state.get("saas_access_token")
    _rest_delete("/rest/v1/app_data",token,params={"tenant_id":f"eq.{tenant_id()}","entity":f"eq.{entity}"})
    payload=[{"tenant_id":tenant_id(),"entity":entity,"record_id":str(i),"payload":row} for i,row in enumerate(rows)]
    if payload: _rest_post("/rest/v1/app_data",token,payload)
