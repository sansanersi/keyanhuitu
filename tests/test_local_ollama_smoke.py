import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
for path in (SYSTEM_DIR, WEB_APP_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import web_app.app as webapp


def _live_smoke_enabled():
    return os.environ.get("RUN_LOCAL_OLLAMA_SMOKE", "").strip() == "1"


@unittest.skipUnless(_live_smoke_enabled(), "set RUN_LOCAL_OLLAMA_SMOKE=1 to call local Ollama")
class LocalOllamaSmokeTest(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()

    def test_ollama_status_reports_downloaded_lightweight_model(self):
        response = self.client.get("/api/ollama/status")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["running"])
        self.assertEqual(payload["default_model"], "qwen2.5:0.5b")
        self.assertIn("qwen2.5:0.5b", payload["models"])

    def test_query_route_uses_local_ollama_model(self):
        response = self.client.post(
            "/api/query",
            json={
                "text": "只回答两个字：可以",
                "model": "qwen2.5:0.5b",
            },
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["source"], "ollama")
        self.assertTrue(payload["response"].strip())
        self.assertNotIn("调用失败", payload["response"])
        self.assertNotIn("模型无响应", payload["response"])


if __name__ == "__main__":
    unittest.main()
