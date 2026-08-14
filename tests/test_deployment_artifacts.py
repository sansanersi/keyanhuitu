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
        self.assertIn("SCI_IMAGE_ASSET_ROOT=", content)

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

    def test_web_settings_ui_uses_model_service_wording(self):
        content = read_text("sci-illust-system/web_app/templates/index.html")

        self.assertIn("模型服务记忆", content)
        self.assertIn("模型服务地址", content)
        self.assertIn("保存模型服务设置", content)
        self.assertIn("模型服务状态", content)
        self.assertNotIn(">Ollama 记忆<", content)
        self.assertNotIn(">Ollama 地址<", content)
        self.assertNotIn("保存 Ollama 设置", content)
        self.assertNotIn("Ollama 状态", content)


    def test_web_ui_uses_same_origin_api_when_served_over_http(self):
        content = read_text("sci-illust-system/web_app/templates/index.html")

        self.assertIn('if (isHttp) return url;', content)
        self.assertIn('return "http://127.0.0.1:5000" + url;', content)
        self.assertNotIn('var isAppServer = isHttp', content)

    def test_nginx_template_sets_proxy_timeouts_for_model_requests(self):
        content = read_text("build/keyanhuitu.nginx.conf")

        self.assertIn("proxy_connect_timeout", content)
        self.assertIn("proxy_send_timeout", content)
        self.assertIn("proxy_read_timeout", content)

    def test_web_ui_uses_isolated_top_level_pages(self):
        content = read_text("sci-illust-system/web_app/templates/index.html")

        self.assertIn("function switchPage(name)", content)
        self.assertIn('.page.active {', content)
        self.assertIn('item.addEventListener("click", function() { switchPage(item.dataset.page); });', content)
        self.assertIn("onclick=\\\"switchPage('drawingApp')\\\"", content)
        self.assertNotIn("function initAnchorNavigation()", content)
        self.assertNotIn("function jumpToPage(name)", content)
        self.assertNotIn('href="#page-dashboard"', content)

    def test_drawing_app_panels_are_not_sticky_fixed(self):
        content = read_text("sci-illust-system/web_app/templates/index.html")

        self.assertIn(".draw-layout {", content)
        self.assertNotIn(".draw-panel .card {\n  position: sticky;", content)
        self.assertNotIn(".preview {\n  display: flex;\n  flex-direction: column;\n  min-height: 650px;\n  position: sticky;", content)

    def test_drawing_app_ui_surfaces_generation_source_labels(self):
        content = read_text("sci-illust-system/web_app/templates/index.html")

        self.assertIn("function sourceLabel(source)", content)
        self.assertIn("来源：", content)
        self.assertIn("模型生成", content)
        self.assertIn("规则生成", content)

    def test_sidebar_uses_workbench_sidebar_shell(self):
        content = read_text("sci-illust-system/web_app/templates/index.html")

        self.assertIn("grid-template-columns: 264px 1fr;", content)
        self.assertIn("padding: 18px 14px;", content)
        self.assertIn("border-right: 1px solid var(--border-soft);", content)
        self.assertIn("background: var(--surface-panel);", content)
        self.assertIn("color: var(--text-strong);", content)
        self.assertIn("gap: 10px;", content)
        self.assertNotIn("backdrop-filter: blur(20px);", content)
        self.assertNotIn("border-radius: 24px;", content)

    def test_web_ui_uses_light_workbench_shell(self):
        content = read_text("sci-illust-system/web_app/templates/index.html")

        self.assertIn('class="app workbench-shell"', content)
        self.assertIn('class="sidebar workbench-sidebar"', content)
        self.assertIn('class="topbar workbench-topbar"', content)
        self.assertIn('class="draw-layout creator-workbench"', content)
        self.assertIn('class="card draw-panel creator-sidebar"', content)
        self.assertIn('class="card preview creator-canvas"', content)
        self.assertIn("--surface-page: #f6f8f4;", content)
        self.assertIn("--accent-soft: #e4f4e8;", content)
        self.assertIn("生成模式", content)
        self.assertIn("图片描述", content)
        self.assertIn("图片分辨率", content)
        self.assertIn("图片生成数量", content)


if __name__ == "__main__":
    unittest.main()
