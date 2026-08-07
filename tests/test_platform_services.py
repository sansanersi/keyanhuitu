import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from web_app.services.text_library_service import TextLibraryService


class FakeCatalog:
    def list_entries(self, domain="", search=""):
        return {"entries": [{"name": "EGFR"}], "total": 1}


class FakeDocuments:
    def list_documents(self):
        return {"documents": [{"name": "paper.txt"}]}

    def text_kb_status(self):
        return {"index_ready": True, "cleaned_documents": 1}


class FakeSearch:
    def search(self, query):
        return {"query": query, "answer": "EGFR answer", "hits": []}


class TextLibraryServiceTest(unittest.TestCase):
    def test_dashboard_merges_text_assets(self):
        service = TextLibraryService(
            catalog_service=FakeCatalog(),
            document_service=FakeDocuments(),
            search_service=FakeSearch(),
        )

        result = service.dashboard()

        self.assertEqual(result["boundary"], "text_library")
        self.assertEqual(result["entries_total"], 1)
        self.assertEqual(result["documents_total"], 1)
        self.assertEqual(result["entries"][0]["name"], "EGFR")
        self.assertEqual(result["documents"][0]["name"], "paper.txt")
        self.assertTrue(result["text_kb_status"]["index_ready"])

    def test_search_delegates_to_search_service(self):
        service = TextLibraryService(
            catalog_service=FakeCatalog(),
            document_service=FakeDocuments(),
            search_service=FakeSearch(),
        )

        result = service.search("EGFR")

        self.assertEqual(result["query"], "EGFR")
        self.assertEqual(result["answer"], "EGFR answer")


class TextLibraryRouteTest(unittest.TestCase):
    def test_text_library_dashboard_route_exposes_text_boundary(self):
        os.environ.setdefault("BIOICONS_ROOT", os.path.join(os.environ.get("TEMP", ROOT), "codex-empty-bioicons-root"))
        os.makedirs(os.environ["BIOICONS_ROOT"], exist_ok=True)
        import web_app.app as webapp

        response = webapp.app.test_client().get("/api/text-library/dashboard")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["boundary"], "text_library")
        self.assertIn("entries_total", payload)
        self.assertIn("documents_total", payload)


if __name__ == "__main__":
    unittest.main()
