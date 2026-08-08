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


class SQLiteToMySQLMigrationTest(unittest.TestCase):
    def test_migration_copies_entries_documents_and_settings(self):
        from web_app.migrations import migrate_knowledge_repository
        from web_app.repositories import SQLiteKnowledgeRepository

        target = RecordingRepository()
        with tempfile.TemporaryDirectory() as tmpdir:
            source = SQLiteKnowledgeRepository(db_path=os.path.join(tmpdir, "knowledge.db"))
            source.add_entry(name="EGFR", english="EGFR", domain="biology", tags=["receptor"])
            source.save_document(filename="paper.txt", filepath="/tmp/paper.txt", file_type="txt", content="EGFR", vectorized=1)
            source.set_setting("ollama_default_model", "qwen2.5:0.5b")

            result = migrate_knowledge_repository(source, target)

        self.assertEqual(result, {"entries": 1, "documents": 1, "settings": 1})
        self.assertEqual(target.entries[0]["name"], "EGFR")
        self.assertEqual(target.documents[0]["filename"], "paper.txt")
        self.assertEqual(target.settings["ollama_default_model"], "qwen2.5:0.5b")

    def test_migration_script_dry_run_reports_sqlite_counts(self):
        from web_app.repositories import SQLiteKnowledgeRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "knowledge.db")
            source = SQLiteKnowledgeRepository(db_path=db_path)
            source.add_entry(name="EGFR", domain="biology")
            source.save_document(filename="paper.txt", filepath="/tmp/paper.txt", content="EGFR")
            source.set_setting("ollama_default_model", "qwen2.5:0.5b")

            result = subprocess.run(
                [sys.executable, "scripts/migrate_sqlite_to_mysql.py", "--sqlite-db", db_path, "--dry-run"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mode"], "dry-run")
        self.assertEqual(payload["counts"], {"entries": 1, "documents": 1, "settings": 1})


class RecordingRepository:
    def __init__(self):
        self.entries = []
        self.documents = []
        self.settings = {}

    def add_entry(self, **kwargs):
        self.entries.append(kwargs)
        return True

    def save_document(self, **kwargs):
        self.documents.append(kwargs)
        return len(self.documents)

    def set_setting(self, key, value):
        self.settings[key] = value


if __name__ == "__main__":
    unittest.main()
