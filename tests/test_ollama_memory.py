import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

from web_app.database import KnowledgeDatabase
import web_app.app as webapp


class OllamaMemoryTest(unittest.TestCase):
    def test_database_settings_persist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "knowledge.db")
            db = KnowledgeDatabase(db_path)

            db.set_setting("ollama_base_url", "http://localhost:11434")
            db.set_setting("ollama_default_model", "qwen3.5:9b")

            self.assertEqual(db.get_setting("ollama_base_url"), "http://localhost:11434")
            self.assertEqual(db.get_setting("ollama_default_model"), "qwen3.5:9b")
            self.assertEqual(
                db.list_settings("ollama_"),
                {
                    "ollama_base_url": "http://localhost:11434",
                    "ollama_default_model": "qwen3.5:9b",
                },
            )
            del db

    def test_ollama_config_route_normalizes_and_persists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "knowledge.db")
            temp_db = KnowledgeDatabase(db_path)
            original_db = webapp.db
            webapp.db = temp_db
            try:
                client = webapp.app.test_client()
                with patch.object(webapp, "_get_ollama_models", return_value=["qwen3.5:9b"]):
                    response = client.post(
                        "/api/ollama/config",
                        json={
                            "base_url": "http://localhost:11434/api",
                            "default_model": "qwen3.5:9b",
                        },
                    )

                payload = response.get_json()
                self.assertEqual(response.status_code, 200)
                self.assertTrue(payload["success"])
                self.assertEqual(payload["base_url"], "http://localhost:11434")
                self.assertEqual(payload["default_model"], "qwen3.5:9b")
                self.assertEqual(temp_db.get_setting("ollama_base_url"), "http://localhost:11434")
                self.assertEqual(temp_db.get_setting("ollama_default_model"), "qwen3.5:9b")
            finally:
                webapp.db = original_db
                del temp_db


if __name__ == "__main__":
    unittest.main()
