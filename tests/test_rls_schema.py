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
            self.assertIn("set search_path = ''", block, name)

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

    def test_invitation_indexes_are_created_after_table(self):
        table_pos = self.sql.index("create table if not exists public.invitations")
        index_pos = self.sql.index("create index if not exists idx_invitations_invited_by")
        self.assertGreater(index_pos, table_pos)

    def test_atomic_save_migration_has_no_invalid_signature_revoke(self):
        migration = (Path(__file__).resolve().parents[1] / "supabase/migrations/20261004_atomic_app_data_batch_save.sql").read_text(encoding="utf-8")
        self.assertNotIn("save_app_data_batch(uuid,text,jsonb,text[])", migration)
        self.assertIn("grant execute on function public.save_app_data_batch(uuid,text,jsonb) to authenticated;", migration)

    def test_security_definer_functions_pin_empty_search_path(self):
        files = [
            "supabase_schema.sql",
            "supabase/migrations/20261004_atomic_app_data_batch_save.sql",
            "supabase/migrations/20261004_atomic_app_data_conflict_hardening.sql",
            "supabase/migrations/20261003222323_owner_role_protection.sql",
        ]
        for rel in files:
            sql = (Path(__file__).resolve().parents[1] / rel).read_text(encoding="utf-8")
            parts = sql.lower().split("security definer")
            for part in parts[1:]:
                self.assertIn("set search_path = ''", part[:120], rel)

    def test_member_role_rpc_cannot_demote_owner(self):
        self.assertIn("CANNOT_CHANGE_OWNER_ROLE", self.sql)
        self.assertIn("if target_current_role = 'owner' then", self.sql)
        self.assertIn("grant execute on function public.set_member_role(uuid,uuid,text) to authenticated;", self.sql)


if __name__ == "__main__":
    unittest.main()
