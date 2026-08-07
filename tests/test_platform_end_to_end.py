import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
for path in (SYSTEM_DIR, WEB_APP_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("BIOICONS_ROOT", os.path.join(os.environ.get("TEMP", ROOT), "codex-empty-bioicons-root"))
os.makedirs(os.environ["BIOICONS_ROOT"], exist_ok=True)

import web_app.app as webapp


class PlatformEndToEndTest(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()

    def test_text_library_dashboard_is_available(self):
        response = self.client.get("/api/text-library/dashboard")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["boundary"], "text_library")
        self.assertIn("entries_total", payload)
        self.assertIn("documents_total", payload)
        self.assertIn("text_kb_status", payload)

    def test_image_library_suggest_returns_unified_asset_payload(self):
        response = self.client.get("/api/image-library/suggest?q=EGFR")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["boundary"], "image_library")
        self.assertEqual(payload["query"], "EGFR")
        self.assertIn("items", payload)
        self.assertIn("total", payload)

    def test_workflow_route_generates_asset_matched_workflow(self):
        response = self.client.post(
            "/api/workflow",
            json={"text": "EGF activates EGFR and then RAS", "canvas_width": 900, "canvas_height": 600},
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["boundary"], "drawing_application")
        self.assertEqual(payload["workflow"]["schema_version"], "1.0")
        self.assertGreaterEqual(len(payload["workflow"]["elements"]), 3)
        self.assertIn("selected_asset", payload["workflow"]["elements"][0])

    def test_draw_route_generates_svg_without_external_model(self):
        response = self.client.post(
            "/api/draw",
            json={
                "text": "EGF activates EGFR and then RAS",
                "layout": "hierarchical",
                "style": "science",
                "canvas_width": 900,
                "canvas_height": 600,
            },
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["boundary"], "drawing_application")
        self.assertIn("<svg", payload["svg"])
        self.assertGreaterEqual(len(payload["elements"]), 1)


if __name__ == "__main__":
    unittest.main()
