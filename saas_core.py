"""SaaS foundation: Supabase Auth + multi-tenant Postgres via PostgREST."""

import hashlib, json, os
from typing import Optional
import requests
import streamlit as st

PLAN_LIMITS={"trial":{"products":100,"users":1,"content":100},"starter":{"products":1000,"users":3,"content":1000},"pro":{"products":10000,"users":10,"content":10000},"business":{"products":100000,"users":50,"content":100000}}

def _cfg(name, default=""):
    try: value=st.secrets.get(name, os.getenv(name, default))
    except Exception: value=os.getenv(name, default)
    return str(value or "").strip()

SUPABASE_URL=_cfg("SUPABASE_URL").rstrip("/")
SUPABASE_ANON_KEY=_cfg("SUPABASE_ANON_KEY")

def saas_enabled(): return bool(SUPABASE_URL and SUPABASE_ANON_KEY)

def demo_mode_enabled():
    return _cfg("DEMO_MODE","false").lower() in ("1","true","yes","on")

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

def request_password_reset(email):
    email=str(email or "").strip().lower()
    if not email:
        raise ValueError("Укажите email.")
    redirect=_cfg("SAAS_PUBLIC_URL").rstrip("/")
    payload={"email":email}
    if redirect:
        payload["redirect_to"]=redirect
    return _request("POST","/auth/v1/recover",json=payload)

def validate_session():
    token=st.session_state.get("saas_access_token")
    if not token:
        return False
    try:
        user=get_user(token)
        tenant=current_tenant(token,user.get("id"))
        if not tenant:
            raise RuntimeError("Магазин не найден.")
        _set_identity(user,tenant)
        return True
    except Exception:
        for k in list(st.session_state):
            if k.startswith("saas_"): del st.session_state[k]
        return False

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

def supabase_health():
    if not saas_enabled():
        return False, "Supabase не настроен: проверьте SUPABASE_URL и SUPABASE_ANON_KEY."
    try:
        _request("GET", "/auth/v1/settings")
        return True, "Supabase Auth доступен."
    except Exception as e:
        return False, f"Supabase недоступен: {e}"

def login_ui():
    st.markdown(
        '<div class="dashboard-hero"><div class="dashboard-hero-kicker">AI BUSINESS PLATFORM</div>'
        '<div class="dashboard-hero-title">Ваш магазин. Один рабочий центр.</div>'
        '<div class="dashboard-hero-text">Каталог, контент, заявки, заказы и AI-помощник MAX — в одном месте.</div></div>',
        unsafe_allow_html=True,
    )
    if saas_enabled():
        ok, message = supabase_health()
        if not ok:
            st.error("Не удалось связаться с сервером аккаунтов. Проверьте настройки Supabase.")
    tab1,tab2,tab3=st.tabs(["Войти","Создать магазин","Восстановить пароль"])
    with tab1:
        email=st.text_input("Email",key="saas_login_email")
        password=st.text_input("Пароль",type="password",key="saas_login_password")
        if st.button("Войти",type="primary",use_container_width=True,key="saas_login"):
            if not email.strip() or not password:
                st.error("Введите email и пароль.")
            else:
                try:
                    with st.spinner("Проверяем аккаунт…"):
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
        st.caption("Стартовая настройка занимает около минуты. После регистрации MAX поможет заполнить магазин.")
        store=st.text_input("Название магазина",placeholder="Например, Demo Store",key="saas_signup_store")
        email=st.text_input("Email владельца",placeholder="you@example.com",key="saas_signup_email")
        password=st.text_input("Пароль",type="password",placeholder="Минимум 8 символов",key="saas_signup_password")
        repeat=st.text_input("Повторите пароль",type="password",key="saas_signup_password2")
        if st.button("Создать магазин и начать",type="primary",use_container_width=True,key="saas_signup"):
            if len(password)<8: st.error("Пароль должен содержать минимум 8 символов.")
            elif password!=repeat: st.error("Пароли не совпадают.")
            elif "@" not in email or "." not in email.split("@")[-1]: st.error("Проверьте email.")
            elif not store.strip(): st.error("Укажите название магазина.")
            else:
                try:
                    with st.spinner("Создаём магазин…"):
                        result=sign_up(email.strip(),password,store.strip())
                    token=result.get("access_token")
                    if not token:
                        st.success("Аккаунт создан. Проверьте почту и подтвердите email. После подтверждения войдите — магазин и тариф Trial создаются автоматически.")
                    else:
                        user=result.get("user") or get_user(token)
                        tenant=current_tenant(token,user.get("id"))
                        if tenant:
                            st.session_state["saas_access_token"]=token
                            _set_identity(user,tenant)
                            st.rerun()
                        else: st.success("Магазин создан. Войдите после подтверждения email.")
                except Exception as e: st.error(f"Не удалось создать магазин: {e}")
    with tab3:
        email=st.text_input("Email для восстановления",key="saas_recovery_email")
        st.caption("На почту придёт ссылка для смены пароля.")
        if st.button("Отправить ссылку",type="primary",use_container_width=True,key="saas_recovery"):
            try:
                with st.spinner("Отправляем письмо…"):
                    request_password_reset(email)
                st.success("Если аккаунт существует, письмо для восстановления отправлено.")
            except Exception as e:
                st.error(f"Не удалось отправить письмо: {e}")

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
        st.caption(f"Роль · {current_role().upper()}")
        if plan in PLAN_LIMITS:
            u=usage_snapshot()
            max_products=PLAN_LIMITS[plan]["products"]
            st.progress(min(1.0, u["products"]/max_products), text=f"Каталог · {u['products']} / {max_products}")
        if saas_enabled():
            try:
                invites=my_invitations()
                for inv in invites:
                    st.info(f"Приглашение: роль «{inv.get('role')}»")
                    if st.button("Принять приглашение", key=f"accept_inv_{inv.get('id')}", use_container_width=True):
                        accept_invitation(inv.get("id"))
                        st.success("Приглашение принято.")
                        st.rerun()
            except Exception:
                pass
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

def _service_key():
    try: value=st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY",""))
    except Exception: value=os.getenv("SUPABASE_SERVICE_ROLE_KEY","")
    return str(value or "").strip()

def activate_paid_subscription(plan, provider_payment_id, payment_method_id=None, provider="yookassa", tenant=None):
    key=_service_key()
    if not key or not saas_enabled():
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY не настроен.")
    tid=tenant or tenant_id()
    headers={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"return=minimal"}
    base=f"{SUPABASE_URL}/rest/v1"
    sub={"plan":plan,"status":"active","provider":provider,"provider_payment_id":provider_payment_id}
    if payment_method_id:
        sub["provider_payment_method_id"]=payment_method_id
    rr=requests.patch(f"{base}/subscriptions",headers=headers,params={"tenant_id":f"eq.{tid}"},json=sub,timeout=20)
    if not rr.ok: raise RuntimeError(rr.text)
    rr=requests.patch(f"{base}/tenants",headers=headers,params={"id":f"eq.{tid}"},json={"plan":plan,"status":"active"},timeout=20)
    if not rr.ok: raise RuntimeError(rr.text)
    st.session_state["saas_plan"]=plan
    st.session_state["saas_tenant_status"]="active"
    return True

def set_auto_renew(enabled):
    tid=tenant_id()
    if not saas_enabled():
        st.session_state["auto_renew"]=bool(enabled)
        return True
    if current_role() not in ("owner","admin"):
        raise PermissionError("Только владелец или администратор может менять автопродление.")
    key=_service_key()
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY не настроен.")
    headers={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"return=minimal"}
    base=f"{SUPABASE_URL}/rest/v1"
    rr=requests.patch(
        f"{base}/subscriptions",
        headers=headers,
        params={"tenant_id":f"eq.{tid}"},
        json={"auto_renew":bool(enabled),"cancel_at_period_end":not bool(enabled)},
        timeout=20,
    )
    if not rr.ok:
        raise RuntimeError(rr.text)
    st.session_state["auto_renew"]=bool(enabled)
    return True

def subscription_snapshot():
    token=st.session_state.get("saas_access_token")
    tid=tenant_id()
    if not saas_enabled() or not token:
        return {"plan":tenant_plan(),"status":"trialing","provider":None,"current_period_end":None,"auto_renew":False,"cancel_at_period_end":False,"next_billing_at":None}
    try:
        row=subscription(token,tid) or {}
        return {
            "plan":row.get("plan",tenant_plan()),
            "status":row.get("status","trialing"),
            "provider":row.get("provider"),
            "current_period_end":row.get("current_period_end"),
            "auto_renew":bool(row.get("auto_renew",False)),
            "cancel_at_period_end":bool(row.get("cancel_at_period_end",False)),
            "next_billing_at":row.get("next_billing_at"),
        }
    except Exception:
        return {"plan":tenant_plan(),"status":"unknown","provider":None,"current_period_end":None,"auto_renew":False,"cancel_at_period_end":False,"next_billing_at":None}

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

def my_invitations():
    token=st.session_state.get("saas_access_token")
    if not saas_enabled() or not token or not st.session_state.get("saas_email"):
        return []
    return _rest_get("/rest/v1/invitations",token,params={"select":"id,email,role,status,expires_at","email":f"eq.{st.session_state.get('saas_email').lower()}","status":"eq.pending","order":"created_at.desc"})

def accept_invitation(invite_id):
    token=st.session_state.get("saas_access_token")
    if not token: raise RuntimeError("Нужно войти в аккаунт.")
    return _request("POST","/rest/v1/rpc/accept_invitation",token=token,json={"invite_id":invite_id})

def team_invitations():
    token=st.session_state.get("saas_access_token")
    if not saas_enabled() or not token:
        return []
    return _rest_get("/rest/v1/invitations",token,params={"select":"id,email,role,status,created_at,expires_at","tenant_id":f"eq.{tenant_id()}","status":"eq.pending","order":"created_at.desc"})

def can(action):
    role=current_role()
    if role=="owner":
        return True
    if action=="read":
        return role in ("admin","manager","editor","viewer")
    if action=="write_data":
        return role in ("admin","manager","editor")
    if action in ("billing","team","settings","manage_roles"):
        return role=="admin"
    return False

def set_member_role(target_user,new_role):
    token=st.session_state.get("saas_access_token")
    if not saas_enabled() or not token:
        return False
    if not can("manage_roles"):
        raise PermissionError("Только владелец или администратор может менять роли.")
    if new_role not in ("admin","manager","editor","viewer"):
        raise ValueError("Недопустимая роль.")
    return _request("POST","/rest/v1/rpc/set_member_role",token=token,json={
        "target_tenant":tenant_id(),
        "target_user":target_user,
        "new_role":new_role,
    })

def create_team_invitation(email,role):
    token=st.session_state.get("saas_access_token")
    if not saas_enabled() or not token:
        return None
    if not can("team"):
        raise PermissionError("Только администратор или владелец может приглашать участников.")
    role=str(role or "viewer").lower()
    if role not in ("admin","manager","editor","viewer"):
        raise ValueError("Недопустимая роль.")
    members=team_members()
    pending=team_invitations()
    max_users=limit("users")
    if max_users and len(members)+len(pending)>=max_users:
        raise ValueError(f"Лимит участников тарифа {tenant_plan().upper()} достигнут.")
    email=email.strip().lower()
    if not email:
        raise ValueError("Укажите email.")
    payload={"tenant_id":tenant_id(),"email":email,"role":role,"invited_by":st.session_state.get("saas_user_id")}
    return _rest_post("/rest/v1/invitations",token,payload)

def onboarding_complete():
    if not saas_enabled():
        return True
    settings=data_load("settings", [])
    return bool(settings and isinstance(settings[0], dict) and settings[0].get("onboarding_complete"))

def render_onboarding():
    st.markdown(
        '<div class="dashboard-hero"><div class="dashboard-hero-kicker">QUICK START</div>'
        '<div class="dashboard-hero-title">Настроим магазин за 60 секунд</div>'
        '<div class="dashboard-hero-text">Эти данные нужны MAX, чтобы писать контент, отвечать клиентам и подсказывать следующие действия. Их можно изменить позже.</div></div>',
        unsafe_allow_html=True,
    )
    with st.form("saas_onboarding_form"):
        business=st.selectbox("Что продаёте?", ["Спортивный магазин","Одежда и обувь","Интернет-магазин","Другое"], key="onb_business")
        city=st.text_input("Город / регион", placeholder="Краснодарский край", key="onb_city")
        telegram=st.text_input("Telegram магазина", placeholder="@your_store", key="onb_telegram")
        instagram=st.text_input("Instagram", placeholder="@your_store", key="onb_instagram")
        shipping=st.selectbox("Доставка", ["По России","По региону","Самовывоз","Другое"], key="onb_shipping")
        submitted=st.form_submit_button("Сохранить и открыть MAX", type="primary", use_container_width=True)
    if submitted:
        try:
            data_save("settings", [{
                "business_type": business, "city": city.strip(), "telegram": telegram.strip(),
                "instagram": instagram.strip(), "shipping": shipping, "onboarding_complete": True
            }])
            st.session_state["saas_onboarding_complete"]=True
            st.success("Магазин настроен. MAX готов к работе.")
            st.rerun()
        except Exception as e:
            st.error(f"Не удалось сохранить настройки магазина: {e}")

def require_saas_access():
    if not saas_enabled():
        if demo_mode_enabled():
            if not st.session_state.get("saas_demo"):
                st.session_state["saas_demo"]=True
                demo={"id":"demo-user","email":"demo@example.com","tenant_id":"demo-tenant","tenant_name":"Demo Store","plan":"pro","status":"active"}
                _set_identity(demo,{"id":"demo-tenant","name":"Demo Store","plan":"pro","status":"active"})
            render_account_bar()
            return True
        st.markdown(
            '<div class="dashboard-hero"><div class="dashboard-hero-kicker">PRODUCTION SETUP</div>'
            '<div class="dashboard-hero-title">Подключите Supabase, чтобы открыть платформу.</div>'
            '<div class="dashboard-hero-text">Для коммерческого режима нужны SUPABASE_URL и SUPABASE_ANON_KEY. После подключения пользователи смогут регистрировать магазины, входить по паролю и работать изолированно по tenant.</div></div>',
            unsafe_allow_html=True,
        )
        st.error("Платформа не запускается в демо-режиме. Добавьте Supabase Secrets в настройках Streamlit.")
        return False
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

def ensure_can_create(entity,current_count=0):
    if not can("write_data"):
        raise PermissionError("У вашей роли нет прав на изменение данных магазина.")
    if not feature_allowed(entity,current_count):
        raise ValueError(f"Лимит {entity} тарифа {tenant_plan().upper()} достигнут.")
    return True

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
    if saas_enabled() and not can("write_data"):
        raise PermissionError("У вашей роли нет прав на изменение данных магазина.")
    if saas_enabled() and entity=="settings" and not can("settings"):
        raise PermissionError("Только администратор или владелец может менять настройки магазина.")
    if not saas_enabled():
        os.makedirs("data",exist_ok=True)
        with open(f"data/{tenant_id()}_{entity}.json","w",encoding="utf-8") as f: json.dump(rows,f,ensure_ascii=False,indent=2)
        return
    token=st.session_state.get("saas_access_token")
    _rest_delete("/rest/v1/app_data",token,params={"tenant_id":f"eq.{tenant_id()}","entity":f"eq.{entity}"})
    payload=[{"tenant_id":tenant_id(),"entity":entity,"record_id":str(i),"payload":row} for i,row in enumerate(rows)]
    if payload: _rest_post("/rest/v1/app_data",token,payload)
