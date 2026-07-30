import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

import web_app.app as webapp


class QueryRouteTest(unittest.TestCase):
    def test_query_route_returns_system_service_response(self):
        original = webapp.system_service.query_llm
        webapp.system_service.query_llm = lambda text, model, base_url, default_model: {
            "response": "ok",
            "source": "ollama",
        }
        try:
            client = webapp.app.test_client()
            response = client.post("/api/query", json={"text": "EGFR", "model": "qwen3.5:4b"})
        finally:
            webapp.system_service.query_llm = original

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["response"], "ok")
        self.assertEqual(payload["source"], "ollama")


if __name__ == "__main__":
    unittest.main()
