import json
import os
import subprocess
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


class MySQLServerReadinessTest(unittest.TestCase):
    def test_offline_readiness_generates_schema_and_dry_run_counts(self):
        from web_app.repositories import SQLiteKnowledgeRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_db = os.path.join(tmpdir, "knowledge.db")
            schema_output = os.path.join(tmpdir, "mysql_schema.sql")
            source = SQLiteKnowledgeRepository(db_path=sqlite_db)
            source.add_entry(name="EGFR", domain="biology")
            source.save_document(filename="paper.txt", filepath="/tmp/paper.txt", content="EGFR")
            source.set_setting("ollama_default_model", "qwen2.5:0.5b")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/mysql_server_readiness.py",
                    "--sqlite-db",
                    sqlite_db,
                    "--schema-output",
                    schema_output,
                    "--offline",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)

        self.assertEqual(payload["mode"], "offline")
        self.assertEqual(payload["schema"]["generated"], True)
        self.assertEqual(payload["migration_dry_run"]["counts"], {"entries": 1, "documents": 1, "settings": 1})
        self.assertEqual(payload["mysql"]["connection_checked"], False)

    def test_apply_flags_require_connection_check(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_db = os.path.join(tmpdir, "knowledge.db")
            schema_output = os.path.join(tmpdir, "mysql_schema.sql")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/mysql_server_readiness.py",
                    "--sqlite-db",
                    sqlite_db,
                    "--schema-output",
                    schema_output,
                    "--apply-schema",
                    "--offline",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--apply-schema cannot be used with --offline", result.stderr)


if __name__ == "__main__":
    unittest.main()
