import unittest

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


class AssetStoreTests(unittest.TestCase):
    def test_put_uses_user_token_and_tenant_folder(self):
        http = FakeHttp(FakeResponse(200))
        ok = asset_store.storage_put("https://x.supabase.co/", "anon", "user-token", TENANT,
                                     "logo.png", b"png", "image/png", http=http)
        self.assertTrue(ok)
        method, url, kwargs = http.calls[0]
        self.assertEqual(url, f"https://x.supabase.co/storage/v1/object/tenant-assets/{TENANT}/logo.png")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer user-token")
        self.assertEqual(kwargs["headers"]["apikey"], "anon")

    def test_put_failure_returns_false_without_raising(self):
        self.assertFalse(asset_store.storage_put("https://x", "a", "t", TENANT, "logo.png", b"", "image/png",
                                                 http=FakeHttp(FakeResponse(403))))
        self.assertFalse(asset_store.storage_put("https://x", "a", "t", TENANT, "logo.png", b"", "image/png",
                                                 http=FakeHttp(error=RuntimeError("down"))))

    def test_get_returns_bytes_or_none(self):
        self.assertEqual(asset_store.storage_get("https://x", "a", "t", TENANT, "logo.png",
                                                 http=FakeHttp(FakeResponse(200, b"data"))), b"data")
        self.assertIsNone(asset_store.storage_get("https://x", "a", "t", TENANT, "logo.png",
                                                  http=FakeHttp(FakeResponse(404))))
        self.assertIsNone(asset_store.storage_get("https://x", "a", "t", TENANT, "logo.png",
                                                  http=FakeHttp(error=RuntimeError("down"))))

    def test_rejects_unsafe_tenant_or_file_name(self):
        http = FakeHttp(FakeResponse(200))
        for tenant, name in (("unknown", "logo.png"), (TENANT, "../logo.png"), (TENANT, "a/b.png")):
            self.assertFalse(asset_store.storage_put("https://x", "a", "t", tenant, name, b"", "image/png", http=http))
        self.assertEqual(http.calls, [])


if __name__ == "__main__":
    unittest.main()
