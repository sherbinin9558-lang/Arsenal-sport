import importlib
import unittest


MODULES = (
    "saas_core",
    "crm_core",
    "free_automation",
    "automation_suite",
    "commerce_core",
)


class CoreImportRegressionTests(unittest.TestCase):
    def test_core_modules_import_cleanly(self):
        for module_name in MODULES:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
