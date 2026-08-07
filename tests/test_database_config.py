import importlib
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

import web_app.database as database_module


class DatabaseConfigTest(unittest.TestCase):
    def test_db_path_can_be_overridden_by_env_var(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "custom", "knowledge.db")
            with patch.dict(os.environ, {"SCI_WEBAPP_DB_PATH": custom_path}, clear=False):
                reloaded = importlib.reload(database_module)
                try:
                    db = reloaded.KnowledgeDatabase()
                    self.assertEqual(db.db_path, os.path.abspath(custom_path))
                    self.assertTrue(os.path.exists(os.path.dirname(db.db_path)))
                finally:
                    importlib.reload(database_module)

    def test_logical_database_config_uses_three_mysql_schemas(self):
        config_env = {
            "SCI_MYSQL_HOST": "127.0.0.1",
            "SCI_MYSQL_PORT": "3307",
            "SCI_MYSQL_USER": "sci_user",
            "SCI_MYSQL_PASSWORD": "secret",
            "SCI_TEXT_DB_NAME": "text_db",
            "SCI_IMAGE_DB_NAME": "image_db",
            "SCI_APP_DB_NAME": "app_db",
        }

        with patch.dict(os.environ, config_env, clear=False):
            config = database_module.logical_database_config()

        self.assertEqual(config["host"], "127.0.0.1")
        self.assertEqual(config["port"], 3307)
        self.assertEqual(config["user"], "sci_user")
        self.assertEqual(config["password"], "secret")
        self.assertEqual(config["schemas"], {"text": "text_db", "image": "image_db", "app": "app_db"})


if __name__ == "__main__":
    unittest.main()
