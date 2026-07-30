import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from web_app.services.catalog_service import CatalogService


class CatalogServiceTest(unittest.TestCase):
    def test_list_entries_wraps_database_result(self):
        class FakeDb:
            def list_entries(self, domain="", search=""):
                return ([{"name": "EGFR"}], 1)

        service = CatalogService(FakeDb(), None, None, None, "biology")

        result = service.list_entries(domain="biology", search="EGFR")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["entries"][0]["name"], "EGFR")

    def test_suggest_bioicons_wraps_icons_and_stats(self):
        class FakeBioicons:
            def suggest(self, text, top_k=8):
                return [{"name": "embryo"}]

            def stats(self):
                return {"available": True, "count": 1}

        service = CatalogService(None, None, None, FakeBioicons(), "biology")

        result = service.suggest_bioicons("embryo", top_k=5)

        self.assertEqual(result["icons"][0]["name"], "embryo")
        self.assertTrue(result["stats"]["available"])

    def test_suggest_elements_merges_kb_and_bioicons(self):
        class FakeElement:
            def __init__(self, data):
                self._data = data

            def to_dict(self):
                return dict(self._data)

        class FakeElementLibrary:
            def suggest(self, text, top_k=8):
                return [FakeElement({"name": "EGFR", "shape": "receptor"})]

        class FakeBioicons:
            def suggest(self, text, top_k=8):
                return [{"name": "EGFR", "shape": "icon"}, {"name": "embryo", "shape": "icon"}]

        service = CatalogService(None, None, FakeElementLibrary(), FakeBioicons(), "biology")

        result = service.suggest_elements("egfr", top_k=8)

        self.assertEqual(len(result["elements"]), 3)
        self.assertEqual(result["elements"][0]["source"], "knowledge_base")
        self.assertEqual(result["elements"][1]["source"], "bioicons")


if __name__ == "__main__":
    unittest.main()
