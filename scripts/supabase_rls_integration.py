"""Live Supabase RLS integration test suite.

Creates isolated Auth users/tenants through the service key, then exercises
PostgREST with each user's real JWT. All test data is removed in finally.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import uuid
from typing import Any

import requests


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class Api:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key

    def request(self, method: str, path: str, *, token: str | None = None,
                json: Any = None, params: dict[str, str] | None = None,
                headers: dict[str, str] | None = None) -> requests.Response:
        request_headers = {"apikey": self.key, "Content-Type": "application/json"}
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        if headers:
            request_headers.update(headers)
        return requests.request(
            method, f"{self.url}{path}", headers=request_headers, json=json,
            params=params, timeout=20,
        )

    def json(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.request(method, path, **kwargs)
        if not response.ok:
            raise AssertionError(
                f"{method} {path} failed: HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )
        return response.json() if response.content else None


def expect_ok(response: requests.Response, label: str) -> Any:
    if not response.ok:
        raise AssertionError(
            f"{label}: expected success, got HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )
    return response.json() if response.content else None


def expect_denied(response: requests.Response, label: str) -> None:
    if response.ok:
        raise AssertionError(f"{label}: expected RLS denial, got HTTP {response.status_code}")
    print(f"RLS denial confirmed for {label}: HTTP {response.status_code}")


def create_user(admin: Api, email: str, password: str) -> str:
    data = admin.json(
        "POST", "/auth/v1/admin/users",
        json={"email": email, "password": password, "email_confirm": True},
    )
    return str(data["id"])


def delete_default_tenants(admin: Api, user_id: str) -> None:
    tenants = admin.json(
        "GET", "/rest/v1/tenants",
        params={"select": "id", "owner_user_id": f"eq.{user_id}"},
    ) or []
    for tenant in tenants:
        tenant_id = str(tenant["id"])
        admin.request("DELETE", "/rest/v1/tenants", params={"id": f"eq.{tenant_id}"})


def delete_user(admin: Api, user_id: str) -> None:
    response = admin.request("DELETE", f"/auth/v1/admin/users/{user_id}")
    if not response.ok and response.status_code != 404:
        print(f"WARNING: cleanup user {user_id} returned HTTP {response.status_code}")


def sign_in(public: Api, email: str, password: str) -> str:
    data = public.json(
        "POST", "/auth/v1/token?grant_type=password",
        json={"email": email, "password": password},
    )
    return str(data["access_token"])


def postgrest(api: Api, token: str, table: str, method: str, **kwargs: Any) -> requests.Response:
    return api.request(method, f"/rest/v1/{table}", token=token, **kwargs)


def jwt_subject(token: str) -> str:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return str(json.loads(base64.urlsafe_b64decode(payload))["sub"])
    except Exception as exc:
        raise AssertionError(f"Unable to decode authenticated JWT subject: {exc}") from exc


def main() -> int:
    url = env("SUPABASE_URL")
    anon_key = env("SUPABASE_ANON_KEY")
    service_key = env("SUPABASE_SERVICE_ROLE_KEY")
    admin = Api(url, service_key)
    public = Api(url, anon_key)

    run_id = uuid.uuid4().hex[:12]
    password = f"RlsTest-{uuid.uuid4().hex}-A9!"
    users: list[str] = []
    tenant_ids: list[str] = []
    roles = ("owner", "admin", "editor", "viewer")
    accounts: dict[str, tuple[str, str]] = {}

    try:
        for tenant_index in (1, 2):
            email = f"rls-{run_id}-t{tenant_index}-owner@example.invalid"
            user_id = create_user(admin, email, password)
            users.append(user_id)
            delete_default_tenants(admin, user_id)
            accounts[f"t{tenant_index}-owner"] = (email, user_id)
            tenant = admin.json(
                "POST", "/rest/v1/tenants",
                json={
                    "name": f"RLS CI {run_id} tenant {tenant_index}",
                    "slug": f"rls-ci-{run_id}-{tenant_index}",
                    "owner_user_id": user_id,
                    "plan": "trial",
                    "status": "active",
                },
                headers={"Prefer": "return=representation"},
            )
            tenant_ids.append(str(tenant[0]["id"]))

        tenant_a, tenant_b = tenant_ids

        for role in roles[1:]:
            email = f"rls-{run_id}-t1-{role}@example.invalid"
            user_id = create_user(admin, email, password)
            users.append(user_id)
            delete_default_tenants(admin, user_id)
            accounts[f"t1-{role}"] = (email, user_id)
            admin.json(
                "POST", "/rest/v1/memberships",
                json={"user_id": user_id, "tenant_id": tenant_a, "role": role},
            )

        for key, tenant_id in (("t1-owner", tenant_a), ("t2-owner", tenant_b)):
            admin.json(
                "POST", "/rest/v1/memberships",
                json={"user_id": accounts[key][1], "tenant_id": tenant_id, "role": "owner"},
            )

        for tenant_id in tenant_ids:
            admin.json(
                "POST", "/rest/v1/app_data",
                json={
                    "tenant_id": tenant_id,
                    "entity": "rls_ci",
                    "record_id": f"seed-{run_id}-{tenant_id[:8]}",
                    "payload": {"run_id": run_id},
                },
            )

        assert len(users) == 5
        assert len(set(users)) == 5, "Auth user creation returned duplicate user IDs"
        print(f"RLS setup complete: 2 tenants, {len(users)} users")

        for account_name, (email, user_id) in accounts.items():
            token = sign_in(public, email, password)
            assert jwt_subject(token) == user_id, f"{account_name}: JWT subject does not match created user"
            expected_tenant = tenant_a if account_name.startswith("t1-") else tenant_b

            memberships = expect_ok(
                postgrest(
                    public, token, "memberships", "GET",
                    params={"select": "tenant_id,role,user_id"},
                ),
                f"{account_name} membership read",
            )
            own_role = account_name.rsplit("-", 1)[-1]
            visible_tenant_rows = [row for row in memberships if row["tenant_id"] == expected_tenant]
            expected_visible_rows = 4 if expected_tenant == tenant_a else 1
            assert len(visible_tenant_rows) == expected_visible_rows, memberships
            assert all(row["tenant_id"] == expected_tenant for row in visible_tenant_rows), memberships
            own_memberships = [row for row in memberships if row["user_id"] == user_id]
            assert own_memberships, memberships
            assert any(row["role"] == own_role for row in own_memberships), memberships
            assert all(row["tenant_id"] == expected_tenant or row["user_id"] == user_id for row in memberships), memberships
            print(f"PASS {account_name}: membership isolation")

            tenants = expect_ok(
                postgrest(
                    public, token, "tenants", "GET",
                    params={"select": "id,owner_user_id"},
                ),
                f"{account_name} tenant read",
            )
            assert len(tenants) == 1
            assert tenants[0]["id"] == expected_tenant
            print(f"PASS {account_name}: tenant isolation")

            rows = expect_ok(
                postgrest(
                    public, token, "app_data", "GET",
                    params={"select": "tenant_id,entity,record_id", "entity": "eq.rls_ci"},
                ),
                f"{account_name} app_data read",
            )
            assert rows, rows
            assert all(row["tenant_id"] == expected_tenant for row in rows), rows
            print(f"PASS {account_name}: app_data isolation")

            foreign = tenant_b if expected_tenant == tenant_a else tenant_a
            foreign_rows = expect_ok(
                postgrest(
                    public, token, "app_data", "GET",
                    params={"select": "tenant_id", "tenant_id": f"eq.{foreign}"},
                ),
                f"{account_name} foreign tenant read",
            )
            assert foreign_rows == []
            print(f"PASS {account_name}: foreign-tenant read blocked")

            suffix = account_name.rsplit("-", 1)[-1]
            record_id = f"insert-{run_id}-{account_name}"
            insert_response = postgrest(
                public, token, "app_data", "POST",
                json={
                    "tenant_id": expected_tenant,
                    "entity": "rls_ci",
                    "record_id": record_id,
                    "payload": {"role": account_name},
                },
                headers={"Prefer": "return=representation"},
            )
            if suffix in {"owner", "admin", "editor"}:
                expect_ok(insert_response, f"{account_name} writer insert")
                print(f"PASS {account_name}: writer insert allowed")
            else:
                expect_denied(insert_response, f"{account_name} viewer insert")

            invitation_response = postgrest(
                public, token, "invitations", "POST",
                json={
                    "tenant_id": expected_tenant,
                    "email": f"rls-{run_id}-{account_name}@example.invalid",
                    "role": "viewer",
                    "invited_by": user_id,
                },
                headers={"Prefer": "return=representation"},
            )
            if suffix in {"owner", "admin"}:
                expect_ok(invitation_response, f"{account_name} invitation insert")
                print(f"PASS {account_name}: admin invitation allowed")
            else:
                expect_denied(invitation_response, f"{account_name} invitation insert")

        print("RLS integration suite: PASS")
        return 0
    finally:
        for tenant_id in tenant_ids:
            admin.request("DELETE", "/rest/v1/app_data", params={"tenant_id": f"eq.{tenant_id}"})
            admin.request("DELETE", "/rest/v1/invitations", params={"tenant_id": f"eq.{tenant_id}"})
            admin.request("DELETE", "/rest/v1/memberships", params={"tenant_id": f"eq.{tenant_id}"})
            admin.request("DELETE", "/rest/v1/tenants", params={"id": f"eq.{tenant_id}"})
        for user_id in users:
            delete_user(admin, user_id)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RLS integration suite: FAIL: {exc}", file=sys.stderr)
        raise
