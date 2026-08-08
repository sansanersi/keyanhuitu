import os
import subprocess
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


class ServerDataLayerTest(unittest.TestCase):
    def test_mysql_schema_uses_three_logical_databases(self):
        from web_app.server_data_layer import mysql_schema_statements

        statements = "\n".join(mysql_schema_statements())

        self.assertIn("CREATE DATABASE IF NOT EXISTS `text_db`", statements)
        self.assertIn("CREATE DATABASE IF NOT EXISTS `image_db`", statements)
        self.assertIn("CREATE DATABASE IF NOT EXISTS `app_db`", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `text_db`.`documents`", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `text_db`.`terms`", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `image_db`.`image_assets`", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `image_db`.`asset_relations`", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `app_db`.`drawing_requests`", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `app_db`.`generated_figures`", statements)
        self.assertNotIn("AUTOINCREMENT", statements)

    def test_mysql_schema_uses_configured_database_names(self):
        from web_app.server_data_layer import mysql_schema_statements

        env = {
            "SCI_TEXT_DB_NAME": "prod_text",
            "SCI_IMAGE_DB_NAME": "prod_image",
            "SCI_APP_DB_NAME": "prod_app",
        }

        with patch.dict(os.environ, env, clear=False):
            statements = "\n".join(mysql_schema_statements())

        self.assertIn("CREATE DATABASE IF NOT EXISTS `prod_text`", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `prod_image`.`image_assets`", statements)
        self.assertIn("CREATE TABLE IF NOT EXISTS `prod_app`.`workflows`", statements)

    def test_generate_mysql_schema_script_writes_sql_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "schema.sql")
            result = subprocess.run(
                [sys.executable, "scripts/generate_mysql_schema.py", "--output", output_path],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            with open(output_path, "r", encoding="utf-8") as handle:
                content = handle.read()

        self.assertIn("CREATE DATABASE IF NOT EXISTS `text_db`", content)
        self.assertIn("CREATE TABLE IF NOT EXISTS `app_db`.`model_configs`", content)


if __name__ == "__main__":
    unittest.main()
