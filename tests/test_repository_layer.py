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

    def test_repository_factory_requires_mysql_driver_when_no_connector_is_injected(self):
        from web_app.repositories import build_repository

        with self.assertRaises(RuntimeError) as context:
            build_repository(kind="mysql")

        self.assertIn("requires PyMySQL", str(context.exception))

    def test_repository_factory_reads_repository_kind_from_env(self):
        from web_app.repositories import MySQLKnowledgeRepository, build_repository

        connection = FakeMySQLConnection()
        with patch.dict(os.environ, {"SCI_REPOSITORY_KIND": "mysql"}, clear=False):
            repository = build_repository(connector=lambda **kwargs: connection)

        self.assertIsInstance(repository, MySQLKnowledgeRepository)

    def test_mysql_repository_uses_three_schema_tables(self):
        from web_app.repositories import MySQLKnowledgeRepository

        connection = FakeMySQLConnection()
        repository = MySQLKnowledgeRepository(
            config={
                "host": "127.0.0.1",
                "port": 3306,
                "user": "sci",
                "password": "",
                "schemas": {"text": "text_db", "image": "image_db", "app": "app_db"},
            },
            connector=lambda **kwargs: connection,
        )

        connection.queue_scalar(0)
        self.assertTrue(repository.add_entry(name="EGFR", english="EGFR", domain="biology"))
        repository.save_document(filename="paper.txt", filepath="/tmp/paper.txt", file_type="txt", content="EGFR", vectorized=1)
        repository.set_setting("ollama_default_model", "qwen2.5:0.5b")

        executed_sql = "\n".join(connection.executed_sql)
        self.assertIn("INSERT INTO `text_db`.`terms`", executed_sql)
        self.assertIn("INSERT INTO `text_db`.`documents`", executed_sql)
        self.assertIn("INSERT INTO `app_db`.`model_configs`", executed_sql)

    def test_repository_factory_can_create_mysql_repository_from_env(self):
        from web_app.repositories import MySQLKnowledgeRepository, build_repository

        connection = FakeMySQLConnection()
        env = {
            "SCI_REPOSITORY_KIND": "mysql",
            "SCI_TEXT_DB_NAME": "prod_text",
            "SCI_IMAGE_DB_NAME": "prod_image",
            "SCI_APP_DB_NAME": "prod_app",
        }

        with patch.dict(os.environ, env, clear=False):
            repository = build_repository(connector=lambda **kwargs: connection)

        self.assertIsInstance(repository, MySQLKnowledgeRepository)
        self.assertEqual(repository.schemas["text"], "prod_text")

    def test_repository_factory_rejects_unknown_repository_kind(self):
        from web_app.repositories import build_repository

        with self.assertRaises(ValueError) as context:
            build_repository(kind="postgres")

        self.assertIn("Unsupported repository kind: postgres", str(context.exception))


if __name__ == "__main__":
    unittest.main()


class FakeMySQLConnection:
    def __init__(self):
        self.executed_sql = []
        self.scalar_queue = []
        self.lastrowid = 1

    def cursor(self):
        return FakeMySQLCursor(self)

    def commit(self):
        pass

    def close(self):
        pass

    def queue_scalar(self, value):
        self.scalar_queue.append(value)


class FakeMySQLCursor:
    def __init__(self, connection):
        self.connection = connection
        self.lastrowid = connection.lastrowid

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.connection.executed_sql.append(sql)
        self.lastrowid = self.connection.lastrowid

    def fetchone(self):
        if self.connection.scalar_queue:
            return {"COUNT(*)": self.connection.scalar_queue.pop(0)}
        return None

    def fetchall(self):
        return []
