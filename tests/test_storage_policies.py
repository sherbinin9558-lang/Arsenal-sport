import re
import unittest
from pathlib import Path

SQL = (Path(__file__).resolve().parents[1] / "supabase_schema.sql").read_text(encoding="utf-8")


class StoragePolicyTests(unittest.TestCase):
    def test_bucket_is_private(self):
        self.assertRegex(SQL, r"values \('tenant-assets', 'tenant-assets', false,")

    def test_every_policy_is_scoped_to_bucket_and_tenant(self):
        policies = re.findall(r'create policy "tenant (?:members|writers) can \w+ assets" on storage\.objects(.*?);\n', SQL, re.S)
        self.assertEqual(len(policies), 4)
        for body in policies:
            self.assertIn("bucket_id = 'tenant-assets'", body)
            self.assertIn("public.storage_object_tenant(name)", body)
            self.assertIn("to authenticated", body)

    def test_writes_require_writer_role_reads_require_membership(self):
        self.assertIn('create policy "tenant members can read assets"', SQL)
        read = SQL.split('create policy "tenant members can read assets"')[1].split(";")[0]
        self.assertIn("is_tenant_member", read)
        for name in ("upload", "update", "delete"):
            body = SQL.split(f'create policy "tenant writers can {name} assets"')[1].split(";")[0]
            self.assertIn("is_tenant_writer", body)

    def test_helper_is_not_callable_by_anonymous(self):
        self.assertIn("revoke all on function public.storage_object_tenant(text) from public;", SQL)
        self.assertIn("revoke execute on function public.storage_object_tenant(text) from anon;", SQL)
        self.assertIn("revoke execute on function public.is_tenant_writer(uuid) from anon;", SQL)


if __name__ == "__main__":
    unittest.main()
