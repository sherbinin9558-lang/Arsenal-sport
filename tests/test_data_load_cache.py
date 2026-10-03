import types
import unittest
from unittest import mock

try:
    import saas_core
    HAS_DEPS = True
except Exception:  # CI without streamlit/requests
    HAS_DEPS = False


def _rows(n=2):
    return [
        {"record_id": f"r{i}", "payload": {"name": f"item {i}", "image": "x" * 50},
         "created_at": "2026-10-01T00:00:00Z", "updated_at": f"2026-10-01T00:00:0{i}Z"}
        for i in range(n)
    ]


@unittest.skipUnless(HAS_DEPS, "streamlit and requests are required")
class DataLoadCacheTests(unittest.TestCase):
    def setUp(self):
        self.state = {"saas_access_token": "tok"}
        self.calls = []
        self.rows = _rows()
        patches = [
            mock.patch.object(saas_core, "st", types.SimpleNamespace(session_state=self.state)),
            mock.patch.object(saas_core, "saas_enabled", lambda: True),
            mock.patch.object(saas_core, "tenant_id", lambda: "tenant-1"),
            mock.patch.object(saas_core, "can", lambda _name: True),
            mock.patch.object(saas_core, "_rest_get", self._rest_get),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _rest_get(self, path, token, params=None):
        self.calls.append(dict(params or {}))
        return list(self.rows)

    def test_repeated_loads_use_one_request(self):
        first = saas_core.data_load("products", [])
        second = saas_core.data_load("products", [])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(first, second)

    def test_callers_get_independent_copies(self):
        first = saas_core.data_load("products", [])
        first[0]["name"] = "changed"
        first.append({"name": "extra"})
        second = saas_core.data_load("products", [])
        self.assertEqual(len(second), 2)
        self.assertNotEqual(second[0]["name"], "changed")

    def test_each_entity_and_tenant_is_cached_separately(self):
        saas_core.data_load("products", [])
        saas_core.data_load("leads", [])
        self.assertEqual(len(self.calls), 2)
        with mock.patch.object(saas_core, "tenant_id", lambda: "tenant-2"):
            saas_core.data_load("products", [])
        self.assertEqual(len(self.calls), 3)

    def test_cache_expires(self):
        times = iter([100.0, 100.0 + saas_core._LOAD_CACHE_TTL + 1, 200.0, 200.0])
        with mock.patch.object(saas_core.time, "monotonic", lambda: next(times)):
            saas_core.data_load("products", [])
            saas_core.data_load("products", [])
        self.assertEqual(len(self.calls), 2)

    def test_empty_table_returns_default_and_resets_baseline(self):
        self.rows = []
        default = []
        self.assertIs(saas_core.data_load("products", default), default)
        self.assertIs(saas_core.data_load("products", default), default)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.state[saas_core._data_session_key("products")], {})

    def test_invalidate_forces_fresh_read(self):
        saas_core.data_load("products", [])
        saas_core._invalidate_data_cache("products")
        saas_core.data_load("products", [])
        self.assertEqual(len(self.calls), 2)

    def test_save_clears_cache_and_refreshes_from_database(self):
        loaded = saas_core.data_load("products", [])
        self.rows = _rows(3)
        saas_core.data_save("products", loaded)  # nothing changed -> no writes, final refresh
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(saas_core.data_load("products", [])), 3)
        self.assertEqual(len(self.calls), 2)


if __name__ == "__main__":
    unittest.main()
