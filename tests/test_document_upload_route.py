import io
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

import web_app.app as webapp


class DocumentUploadRouteTest(unittest.TestCase):
    def test_upload_route_returns_processor_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_upload_dir = webapp.dp.upload_dir
            webapp.dp.upload_dir = tmpdir
            client = webapp.app.test_client()
            try:
                response = client.post(
                    "/api/document/upload",
                    data={"file": (io.BytesIO(b"EGFR signaling"), "note.md")},
                    content_type="multipart/form-data",
                )
            finally:
                webapp.dp.upload_dir = original_upload_dir

        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["filename"], "note.md")


if __name__ == "__main__":
    unittest.main()
