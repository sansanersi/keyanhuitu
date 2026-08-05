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


class WorkflowRouteTest(unittest.TestCase):
    def test_workflow_route_returns_missing_text_error(self):
        response = webapp.app.test_client().post("/api/workflow", json={})

        payload = response.get_json()

        self.assertEqual(payload["success"], False)
        self.assertEqual(payload["error"], "请输入绘图需求")

    def test_workflow_route_returns_structured_workflow(self):
        response = webapp.app.test_client().post(
            "/api/workflow",
            json={"text": "EGF activates EGFR and then RAS", "canvas_width": 900, "canvas_height": 600},
        )

        payload = response.get_json()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["workflow"]["schema_version"], "1.0")
        self.assertEqual(payload["workflow"]["composition"]["canvas"], {"width": 900, "height": 600})
        self.assertEqual(payload["errors"], [])
        self.assertGreaterEqual(len(payload["workflow"]["elements"]), 3)
        self.assertIn("selected_asset", payload["workflow"]["elements"][0])
        self.assertGreaterEqual(len(payload["workflow"]["elements"][0]["asset_matches"]), 1)


if __name__ == "__main__":
    unittest.main()
