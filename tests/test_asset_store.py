import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import asset_store

TENANT = "123e4567-e89b-12d3-a456-426614174000"


class FakeResponse:
    def __init__(self, status_code=200, content=b""):
        self.status_code = status_code
        self.content = content


class FakeHttp:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def _do(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if self.error:
            raise self.error
        return self.response

    def post(self, url, **kwargs):
        return self._do("post", url, **kwargs)

    def get(self, url, **kwargs):
        return self._do("get", url, **kwargs)


class FakeStreamlit:
    def __init__(self):
        self.session_state = {}


class AssetStoreTests(unittest.TestCase):
    def test_put_uses_user_token_and_tenant_folder(self):
        http = FakeHttp(FakeResponse(200))
        ok = asset_store.storage_put(
            "https://x.supabase.co/",
            "anon",
            "user-token",
            TENANT,
            "logo.png",
            b"png",
            "image/png",
            http=http,
        )
        self.assertTrue(ok)
        method, url, kwargs = http.calls[0]
        self.assertEqual(
            url,
            f"https://x.supabase.co/storage/v1/object/tenant-assets/{TENANT}/logo.png",
        )
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer user-token")
        self.assertEqual(kwargs["headers"]["apikey"], "anon")

    def test_put_failure_returns_false_without_raising(self):
        self.assertFalse(
            asset_store.storage_put(
                "https://x",
                "a",
                "t",
                TENANT,
                "logo.png",
                b"",
                "image/png",
                http=FakeHttp(FakeResponse(403)),
            )
        )
        self.assertFalse(
            asset_store.storage_put(
                "https://x",
                "a",
                "t",
                TENANT,
                "logo.png",
                b"",
                "image/png",
                http=FakeHttp(error=RuntimeError("down")),
            )
        )

    def test_get_returns_bytes_or_none(self):
        self.assertEqual(
            asset_store.storage_get(
                "https://x", "a", "t", TENANT, "logo.png",
                http=FakeHttp(FakeResponse(200, b"data")),
            ),
            b"data",
        )
        self.assertIsNone(
            asset_store.storage_get(
                "https://x", "a", "t", TENANT, "logo.png",
                http=FakeHttp(FakeResponse(404)),
            )
        )
        self.assertIsNone(
            asset_store.storage_get(
                "https://x", "a", "t", TENANT, "logo.png",
                http=FakeHttp(error=RuntimeError("down")),
            )
        )

    def test_rejects_unsafe_tenant_or_file_name(self):
        http = FakeHttp(FakeResponse(200))
        for tenant, name in (
            ("unknown", "logo.png"),
            (TENANT, "../logo.png"),
            (TENANT, "a/b.png"),
        ):
            self.assertFalse(
                asset_store.storage_put(
                    "https://x", "a", "t", tenant, name, b"", "image/png", http=http
                )
            )
        self.assertEqual(http.calls, [])

    def test_production_save_never_writes_local_on_storage_failure(self):
        fake_st = FakeStreamlit()
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            asset_store, "_session",
            return_value=(fake_st, "https://x.supabase.co", "anon", "user-token", TENANT),
        ), patch.object(asset_store, "storage_put", return_value=False), patch.object(
            asset_store, "_demo_mode", return_value=False
        ):
            local_path = Path(tmp) / "logo.png"
            with self.assertRaises(asset_store.AssetStoreError):
                asset_store.save_asset_bytes(
                    "logo.png", b"png", "image/png", local_path=local_path
                )
            self.assertFalse(local_path.exists())
            self.assertEqual(fake_st.session_state, {})

    def test_production_save_does_not_create_local_copy_on_success(self):
        fake_st = FakeStreamlit()
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            asset_store, "_session",
            return_value=(fake_st, "https://x.supabase.co", "anon", "user-token", TENANT),
        ), patch.object(asset_store, "storage_put", return_value=True), patch.object(
            asset_store, "_demo_mode", return_value=False
        ):
            local_path = Path(tmp) / "logo.png"
            ref = asset_store.save_asset_bytes(
                "logo.png", b"png", "image/png", local_path=local_path
            )
            self.assertEqual(ref, f"storage://tenant-assets/{TENANT}/logo.png")
            self.assertFalse(local_path.exists())
            self.assertEqual(fake_st.session_state, {})

    def test_demo_save_can_use_local_disk(self):
        fake_st = FakeStreamlit()
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            asset_store, "_session",
            return_value=(fake_st, "", "", None, "unknown"),
        ), patch.object(asset_store, "_demo_mode", return_value=True):
            local_path = Path(tmp) / "logo.png"
            ref = asset_store.save_asset_bytes(
                "logo.png", b"png", "image/png", local_path=local_path
            )
            self.assertEqual(ref, str(local_path))
            self.assertEqual(local_path.read_bytes(), b"png")


if __name__ == "__main__":
    unittest.main()
