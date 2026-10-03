import re
import unittest
from pathlib import Path


SCHEMA = Path(__file__).resolve().parents[1] / "supabase_schema.sql"


class RlsSchemaRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = SCHEMA.read_text(encoding="utf-8")

    def test_rls_enabled_on_core_tenant_tables(self):
        for table in ("tenants", "memberships", "subscriptions", "app_data"):
            self.assertRegex(
                self.sql,
                rf"alter table public\.{table} enable row level security;",
                table,
            )

    def test_tenant_helpers_are_security_definer_and_locked_down(self):
        for name in ("is_tenant_member", "is_tenant_writer", "is_tenant_admin"):
            fn = rf"create or replace function public\.{name}\(target_tenant uuid\)(.*?)(?=create or replace function public\.|alter table public\.invitations)",
            self.assertRegex(self.sql, fn[0], name)
            self.assertIn(
                f"revoke all on function public.{name}(uuid) from public;",
                self.sql,
            )
            self.assertIn(
                f"grant execute on function public.{name}(uuid) to authenticated;",
                self.sql,
            )

    def test_helper_grants_follow_function_definitions(self):
        for name in ("is_tenant_member", "is_tenant_writer", "is_tenant_admin"):
            fn_pos = self.sql.index(f"create or replace function public.{name}")
            grant_pos = self.sql.index(
                f"grant execute on function public.{name}(uuid) to authenticated;"
            )
            self.assertLess(fn_pos, grant_pos, name)

    def test_tenant_helpers_use_fixed_search_path(self):
        for name in ("is_tenant_member", "is_tenant_writer", "is_tenant_admin"):
            fn_pos = self.sql.index(f"create or replace function public.{name}")
            next_fn = self.sql.find(
                "create or replace function public.", fn_pos + 1
            )
            block = self.sql[fn_pos:] if next_fn == -1 else self.sql[fn_pos:next_fn]
            self.assertIn("security definer", block.lower(), name)
            self.assertIn("set search_path = public", block, name)

    def test_app_data_policy_matrix_is_present(self):
        required = (
            'for select using (public.is_tenant_member(tenant_id));',
            'for insert with check (public.is_tenant_writer(tenant_id));',
            'for update using (public.is_tenant_writer(tenant_id))',
            'with check (public.is_tenant_writer(tenant_id));',
            'for delete using (public.is_tenant_writer(tenant_id));',
        )
        for fragment in required:
            self.assertIn(fragment, self.sql)

    def test_tenant_update_requires_admin(self):
        self.assertIn(
            'for update using (public.is_tenant_admin(id))',
            self.sql,
        )
        self.assertIn(
            'with check (public.is_tenant_admin(id));',
            self.sql,
        )


if __name__ == "__main__":
    unittest.main()
