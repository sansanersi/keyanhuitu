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


if __name__ == "__main__":
    unittest.main()
