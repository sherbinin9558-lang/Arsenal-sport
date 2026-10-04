import unittest
from unittest.mock import patch

import webmcp_tools


class WebMCPDataRegressionTests(unittest.TestCase):
    def test_webmcp_data_reads_authenticated_store_data(self):
        fixtures = {
            "settings": [{
                "business_type": "Спортивный магазин",
                "city": "Краснодар",
                "telegram": "@arsenal",
                "secret": "must-not-leak",
            }],
            "products": [{
                "_saas_record_id": "p1",
                "name": "Бутсы",
                "brand": "Test",
                "category": "Кроссовки",
                "sport": "Футбол",
                "description": "Test product",
                "size": "42",
                "stock": 3,
                "price": 99999,
            }],
            "content_plan": [{"title": "Test post"}],
        }

        def fake_data_load(entity, default):
            return fixtures.get(entity, default)

        with patch.object(webmcp_tools, "data_load", side_effect=fake_data_load):
            data = webmcp_tools._webmcp_data()

        self.assertEqual(data["settings"]["city"], "Краснодар")
        self.assertNotIn("secret", data["settings"])
        self.assertEqual(data["products"][0]["_saas_record_id"], "p1")
        self.assertNotIn("price", data["products"][0])
        self.assertEqual(data["content_plan"], fixtures["content_plan"])


if __name__ == "__main__":
    unittest.main()
