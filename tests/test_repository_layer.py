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


class RepositoryLayerTest(unittest.TestCase):
    def test_sqlite_repository_preserves_knowledge_database_contract(self):
        from web_app.repositories import SQLiteKnowledgeRepository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "knowledge.db")
            repository = SQLiteKnowledgeRepository(db_path=db_path)

            self.assertTrue(repository.add_entry(name="EGFR", english="EGFR", domain="biology"))
            entries, total = repository.list_entries(domain="biology")
            document_id = repository.save_document(
                filename="paper.txt",
                filepath=os.path.join(tmpdir, "paper.txt"),
                file_type="txt",
                content="EGFR pathway",
                vectorized=1,
            )
            repository.set_setting("ollama_default_model", "qwen2.5:0.5b")

            self.assertEqual(total, 1)
            self.assertEqual(entries[0]["name"], "EGFR")
            self.assertEqual(document_id, 1)
            self.assertEqual(repository.stats["documents"], 1)
            self.assertEqual(repository.stats["vectorized_documents"], 1)
            self.assertEqual(repository.get_setting("ollama_default_model"), "qwen2.5:0.5b")

    def test_repository_factory_defaults_to_sqlite_repository(self):
        from web_app.repositories import SQLiteKnowledgeRepository, build_repository

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "knowledge.db")
            repository = build_repository(db_path=db_path)

            self.assertIsInstance(repository, SQLiteKnowledgeRepository)
            self.assertTrue(os.path.exists(db_path))

    def test_repository_factory_rejects_unsupported_repository_kind(self):
        from web_app.repositories import build_repository

        with self.assertRaises(ValueError) as context:
            build_repository(kind="mysql")

        self.assertIn("Unsupported repository kind", str(context.exception))

    def test_repository_factory_reads_repository_kind_from_env(self):
        from web_app.repositories import build_repository

        with patch.dict(os.environ, {"SCI_REPOSITORY_KIND": "mysql"}, clear=False):
            with self.assertRaises(ValueError) as context:
                build_repository()

        self.assertIn("Unsupported repository kind: mysql", str(context.exception))


if __name__ == "__main__":
    unittest.main()
