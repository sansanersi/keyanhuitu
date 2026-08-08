import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_text(relative_path):
    with open(os.path.join(ROOT, relative_path), "r", encoding="utf-8") as handle:
        return handle.read()


class DeploymentArtifactsTest(unittest.TestCase):
    def test_server_env_template_contains_runtime_boundaries(self):
        content = read_text(".env.server.example")

        self.assertIn("SCI_WEB_HOST=0.0.0.0", content)
        self.assertIn("SCI_WEB_PORT=5000", content)
        self.assertIn("SCI_REPOSITORY_KIND=sqlite", content)
        self.assertIn("SCI_WEBAPP_DB_PATH=", content)
        self.assertIn("SCI_TEXT_DB_NAME=text_db", content)
        self.assertIn("SCI_IMAGE_DB_NAME=image_db", content)
        self.assertIn("SCI_APP_DB_NAME=app_db", content)
        self.assertIn("OLLAMA_DEFAULT_MODEL=qwen2.5:0.5b", content)
        self.assertIn("BIOICONS_ROOT=", content)

    def test_start_server_script_sets_required_env_vars(self):
        content = read_text("scripts/start_server.ps1")

        self.assertIn("SCI_WEB_HOST", content)
        self.assertIn("SCI_WEB_PORT", content)
        self.assertIn("SCI_WEB_MODE", content)
        self.assertIn("BIOICONS_ROOT", content)
        self.assertIn("PYTHONPATH", content)
        self.assertIn("sci-illust-system\\web_app", content)

    def test_health_check_script_covers_core_platform_endpoints(self):
        content = read_text("scripts/health_check.ps1")

        self.assertIn("/api/dashboard", content)
        self.assertIn("/api/text-library/dashboard", content)
        self.assertIn("/api/image-library/dashboard", content)
        self.assertIn("/api/draw/models", content)
        self.assertIn("OllamaUrl", content)

    def test_deployment_document_names_current_limitations(self):
        content = read_text("docs/server_deployment.md")

        self.assertIn("服务器版 v1", content)
        self.assertIn("MySQL", content)
        self.assertIn("SQLite", content)
        self.assertIn("Ollama", content)
        self.assertIn("health_check.ps1", content)
        self.assertIn("server_data_layer.md", content)
        self.assertIn("generate_mysql_schema.py", content)
        self.assertIn("migrate_sqlite_to_mysql.py", content)
        self.assertIn("mysql_server_readiness.py", content)
        self.assertIn("mysql_server_readiness.ps1", content)

    def test_server_data_layer_document_links_schema_generator(self):
        content = read_text("docs/server_data_layer.md")

        self.assertIn("text_db", content)
        self.assertIn("image_db", content)
        self.assertIn("app_db", content)
        self.assertIn("generate_mysql_schema.py", content)
        self.assertIn("migrate_sqlite_to_mysql.py", content)
        self.assertIn("mysql_server_readiness.py", content)
        self.assertIn("mysql_server_readiness.ps1", content)

    def test_mysql_readiness_wrapper_forwards_key_flags(self):
        content = read_text("scripts/mysql_server_readiness.ps1")

        self.assertIn("mysql_server_readiness.py", content)
        self.assertIn("--offline", content)
        self.assertIn("--check-connection", content)
        self.assertIn("--apply-schema", content)
        self.assertIn("--apply-migration", content)


if __name__ == "__main__":
    unittest.main()
