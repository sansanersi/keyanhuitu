import os
import sys
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

import web_app.app as webapp


class TextKBSearchRouteTest(unittest.TestCase):
    def test_search_route_merges_keyword_results_with_text_kb_answer(self):
        client = webapp.app.test_client()
        with patch.object(webapp.kb, "query", return_value=[{"name": "EGFR"}]), patch.object(
            webapp.kb,
            "get_context_snippets",
            return_value=[{"title": "EGFR pathway", "preview": "Signal cascade", "score": 0.91}],
        ), patch.object(
            webapp.text_kb,
            "status",
            return_value={"domain": "biology", "index_ready": True, "cleaned_documents": 3},
        ), patch.object(
            webapp.text_kb,
            "query",
            return_value={
                "available": True,
                "method": "local",
                "query": "EGFR 信号通路",
                "answer": "GraphRAG answer",
            },
        ):
            response = client.get("/api/search?q=EGFR%20%E4%BF%A1%E5%8F%B7%E9%80%9A%E8%B7%AF")

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["results"], [{"name": "EGFR"}])
        self.assertEqual(payload["snippets"][0]["title"], "EGFR pathway")
        self.assertTrue(payload["text_kb_status"]["index_ready"])
        self.assertEqual(payload["text_kb"]["answer"], "GraphRAG answer")
        self.assertEqual(payload["text_kb"]["method"], "local")


if __name__ == "__main__":
    unittest.main()
