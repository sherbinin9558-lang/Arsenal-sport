import unittest
from unittest.mock import patch

import saas_core


class SaasCoreHeadersTests(unittest.TestCase):
    def test_headers_use_anon_key_and_access_token(self):
        with patch.object(saas_core, "_supabase_config", return_value=("https://example.supabase.co", "anon-key")):
            self.assertEqual(saas_core._headers("access-token"), {
                "apikey": "anon-key",
                "Authorization": "Bearer access-token",
                "Content-Type": "application/json",
            })

    def test_headers_fall_back_to_anon_key(self):
        with patch.object(saas_core, "_supabase_config", return_value=("https://example.supabase.co", "anon-key")):
            self.assertEqual(saas_core._headers(), {
                "apikey": "anon-key",
                "Authorization": "Bearer anon-key",
                "Content-Type": "application/json",
            })

    def test_headers_fail_without_anon_key(self):
        with patch.object(saas_core, "_supabase_config", return_value=("https://example.supabase.co", "")):
            with self.assertRaises(saas_core.SupabaseRequestError):
                saas_core._headers("access-token")


if __name__ == "__main__":
    unittest.main()
