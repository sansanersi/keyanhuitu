# 科研绘图平台拆分 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前“科研绘图工作台”按文本库、图片库、应用平台三个边界渐进拆分，同时保持现有 Flask 单体可运行。

**Architecture:** 第一阶段不拆成多个部署服务，而是在现有 Flask 应用内先完成信息架构、页面模块、服务边界和配置边界拆分。数据层以一个 MySQL 实例承载 `text_db`、`image_db`、`app_db` 三个逻辑库为目标，但实现上先加入配置和接口抽象，避免一次性迁移 SQLite/运行态数据导致系统不可用。

**Tech Stack:** Python 3、Flask、unittest、现有服务层、MySQL 目标设计、当前本地运行态数据库兼容。

## Global Constraints

- 所有用户可见文案、代码注释和文档默认使用中文。
- 不提交运行态数据库、PPT、临时目录、缓存文件。
- 现阶段保留当前 Flask 单体运行方式，不能破坏 `start.bat` 和 `start-dev.bat`。
- 测试命令使用 `python -m unittest discover -s tests -p "test_*.py" -v`。
- 测试前可设置 `BIOICONS_ROOT` 为空目录，避免大素材目录拖慢测试。
- 一个 MySQL 实例，三个逻辑库：`text_db`、`image_db`、`app_db`。
- 文本库负责知识，图片库负责素材，应用平台负责生成。

---

## File Structure

计划最终形成以下边界：

```text
sci-illust-system/web_app/
├─ app.py                         继续作为 Flask 路由入口
├─ database.py                    保留当前运行态 DB 兼容，新增逻辑库配置读取
├─ services/
│  ├─ text_library_service.py      文本库聚合服务
│  ├─ image_library_service.py     图片库聚合服务
│  ├─ drawing_app_service.py       应用平台聚合服务
│  ├─ catalog_service.py           逐步归入 text_library_service
│  ├─ document_service.py          逐步归入 text_library_service
│  ├─ search_service.py            逐步归入 text_library_service
│  └─ draw_service.py              逐步归入 drawing_app_service
└─ templates/
   └─ index.html                   第一阶段继续单文件，但按新页面结构重排

tests/
├─ test_platform_navigation.py      新页面边界测试
├─ test_platform_services.py        新聚合服务契约测试
└─ test_database_config.py          扩展逻辑库配置测试
```

拆分顺序：

1. 先改页面导航和命名，形成文本库、图片库、应用平台。
2. 再加服务聚合层，让路由依赖新边界。
3. 再加 MySQL 逻辑库配置抽象。
4. 最后规划数据迁移，不在第一批代码里直接迁移真实数据。

---

### Task 1: 页面信息架构拆分

**Files:**
- Modify: `sci-illust-system/web_app/templates/index.html`
- Test: `tests/test_platform_navigation.py`

**Interfaces:**
- Consumes: 现有前端页面切换函数 `switchPage(name)`、`PAGE_TITLES`、导航按钮 `data-page`
- Produces: 新页面入口 `dashboard`、`textLibrary`、`imageLibrary`、`drawingApp`、`settings`

- [ ] **Step 1: Write the failing test**

Create `tests/test_platform_navigation.py`:

```python
import unittest
from pathlib import Path


class PlatformNavigationTest(unittest.TestCase):
    def setUp(self):
        self.template = Path(
            "sci-illust-system/web_app/templates/index.html"
        ).read_text(encoding="utf-8")

    def test_navigation_exposes_platform_boundaries(self):
        self.assertIn('data-page="textLibrary"', self.template)
        self.assertIn('data-page="imageLibrary"', self.template)
        self.assertIn('data-page="drawingApp"', self.template)
        self.assertIn(">文本库<", self.template)
        self.assertIn(">图片库<", self.template)
        self.assertIn(">应用平台<", self.template)

    def test_old_asset_management_pages_are_not_primary_navigation(self):
        self.assertNotIn('data-page="entries" type="button">知识条目', self.template)
        self.assertNotIn('data-page="documents" type="button">文档管理', self.template)
        self.assertNotIn('data-page="search" type="button">知识检索', self.template)
        self.assertNotIn('data-page="elements" type="button">元素库', self.template)

    def test_generation_area_is_named_as_application_output(self):
        self.assertIn("生成图", self.template)
        self.assertIn("AI 绘图流程", self.template)
        self.assertIn("导出", self.template)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_platform_navigation -v
```

Expected: FAIL because `textLibrary`、`imageLibrary`、`drawingApp` are not yet in the template.

- [ ] **Step 3: Update navigation and page titles**

Modify `sci-illust-system/web_app/templates/index.html` navigation from:

```html
<button class="nav-item active" data-page="dashboard" type="button">仪表盘</button>
<button class="nav-item" data-page="entries" type="button">知识条目</button>
<button class="nav-item" data-page="draw" type="button">科研绘图</button>
<button class="nav-item" data-page="documents" type="button">文档管理</button>
<button class="nav-item" data-page="search" type="button">知识检索</button>
<button class="nav-item" data-page="elements" type="button">元素库</button>
<button class="nav-item" data-page="settings" type="button">设置</button>
```

to:

```html
<button class="nav-item active" data-page="dashboard" type="button">仪表盘</button>
<button class="nav-item" data-page="textLibrary" type="button">文本库</button>
<button class="nav-item" data-page="imageLibrary" type="button">图片库</button>
<button class="nav-item" data-page="drawingApp" type="button">应用平台</button>
<button class="nav-item" data-page="settings" type="button">设置</button>
```

Update `PAGE_TITLES` to:

```javascript
var PAGE_TITLES = {
  dashboard: "仪表盘",
  textLibrary: "文本库",
  imageLibrary: "图片库",
  drawingApp: "应用平台",
  settings: "设置"
};
```

Update `PAGE_SUBTITLES` or the existing subtitle mapping to:

```javascript
var PAGE_SUBTITLES = {
  dashboard: "科研绘图平台总览",
  textLibrary: "论文、图注、术语和 RAG 知识",
  imageLibrary: "图片、图元、Bioicons 和元素关系",
  drawingApp: "需求、AI 绘图流程、生成图和导出",
  settings: "模型和本地服务配置"
};
```

- [ ] **Step 4: Preserve old panels under new containers**

In the HTML panel area:

- Move existing `entries`、`documents`、`search` content into a `textLibrary` page container.
- Move existing `elements` and Bioicons-related content into an `imageLibrary` page container.
- Move existing `draw` content into a `drawingApp` page container.

The generated DOM should keep old element IDs such as `entries-table`、`documents-list`、`search-input`、`draw-input` so existing JavaScript functions do not break.

- [ ] **Step 5: Update page switch initialization**

Modify `switchPage(name)` so:

```javascript
if (name === "textLibrary") {
  loadEntries();
  loadDocuments();
}
if (name === "imageLibrary") {
  loadElementSuggestions();
}
if (name === "drawingApp") {
  loadDrawOptions();
}
```

Do not delete existing loader functions.

- [ ] **Step 6: Run focused test**

Run:

```powershell
python -m unittest tests.test_platform_navigation -v
```

Expected: PASS.

- [ ] **Step 7: Run route tests that exercise the template**

Run:

```powershell
python -m unittest tests.test_workflow_route tests.test_document_upload_route tests.test_text_kb_search_route -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add sci-illust-system/web_app/templates/index.html tests/test_platform_navigation.py
git commit -m "refactor(web): split platform navigation by domain"
```

---

### Task 2: 文本库聚合服务

**Files:**
- Create: `sci-illust-system/web_app/services/text_library_service.py`
- Modify: `sci-illust-system/web_app/services/__init__.py`
- Modify: `sci-illust-system/web_app/app.py`
- Test: `tests/test_platform_services.py`

**Interfaces:**
- Consumes: `CatalogService`、`DocumentService`、`SearchService`
- Produces: `TextLibraryService.dashboard() -> dict`、`TextLibraryService.search(query: str) -> dict`

- [ ] **Step 1: Write the failing service test**

Create `tests/test_platform_services.py`:

```python
import unittest

from services.text_library_service import TextLibraryService


class FakeCatalog:
    def list_entries(self, args):
        return {"items": [{"name": "EGFR"}], "total": 1}


class FakeDocuments:
    def list_documents(self):
        return {"items": [{"name": "paper.txt"}], "total": 1}


class FakeSearch:
    def search(self, query):
        return {"query": query, "answer": "EGFR answer", "hits": []}


class TextLibraryServiceTest(unittest.TestCase):
    def test_dashboard_merges_text_assets(self):
        service = TextLibraryService(
            catalog_service=FakeCatalog(),
            document_service=FakeDocuments(),
            search_service=FakeSearch(),
        )

        result = service.dashboard()

        self.assertEqual(result["entries_total"], 1)
        self.assertEqual(result["documents_total"], 1)
        self.assertEqual(result["boundary"], "text_library")

    def test_search_delegates_to_search_service(self):
        service = TextLibraryService(
            catalog_service=FakeCatalog(),
            document_service=FakeDocuments(),
            search_service=FakeSearch(),
        )

        result = service.search("EGFR")

        self.assertEqual(result["query"], "EGFR")
        self.assertEqual(result["answer"], "EGFR answer")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_platform_services -v
```

Expected: FAIL because `services.text_library_service` does not exist.

- [ ] **Step 3: Implement `TextLibraryService`**

Create `sci-illust-system/web_app/services/text_library_service.py`:

```python
class TextLibraryService:
    """文本库聚合服务，负责把知识条目、文档和检索能力收束到文本库边界。"""

    def __init__(self, catalog_service, document_service, search_service):
        self.catalog_service = catalog_service
        self.document_service = document_service
        self.search_service = search_service

    def dashboard(self):
        entries = self.catalog_service.list_entries({})
        documents = self.document_service.list_documents()
        return {
            "boundary": "text_library",
            "entries_total": entries.get("total", len(entries.get("items", []))),
            "documents_total": documents.get("total", len(documents.get("items", []))),
            "entries": entries.get("items", []),
            "documents": documents.get("items", []),
        }

    def search(self, query):
        return self.search_service.search(query)
```

- [ ] **Step 4: Export service in `services/__init__.py`**

Add:

```python
from .text_library_service import TextLibraryService
```

and include `"TextLibraryService"` in `__all__`.

- [ ] **Step 5: Wire route in `app.py`**

In `_build_runtime_state()`, instantiate:

```python
text_library_service = TextLibraryService(
    catalog_service=catalog_service,
    document_service=document_service,
    search_service=search_service,
)
```

Add it to runtime state:

```python
"text_library_service": text_library_service,
```

Add route:

```python
@app.route("/api/text-library/dashboard")
def text_library_dashboard():
    return jsonify(runtime["text_library_service"].dashboard())
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
python -m unittest tests.test_platform_services tests.test_catalog_service tests.test_document_upload_route tests.test_text_kb_search_route -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add sci-illust-system/web_app/services/text_library_service.py sci-illust-system/web_app/services/__init__.py sci-illust-system/web_app/app.py tests/test_platform_services.py
git commit -m "refactor(web): add text library service boundary"
```

---

### Task 3: 图片库聚合服务

**Files:**
- Create: `sci-illust-system/web_app/services/image_library_service.py`
- Modify: `sci-illust-system/web_app/services/__init__.py`
- Modify: `sci-illust-system/web_app/app.py`
- Test: `tests/test_platform_services.py`

**Interfaces:**
- Consumes: `CatalogService.suggest_elements(args)`、`CatalogService.suggest_bioicons(args)`
- Produces: `ImageLibraryService.dashboard() -> dict`、`ImageLibraryService.suggest_assets(query: str) -> dict`

- [ ] **Step 1: Extend failing test**

Append to `tests/test_platform_services.py`:

```python
from services.image_library_service import ImageLibraryService


class FakeImageCatalog:
    def suggest_elements(self, args):
        return {"items": [{"name": "细胞膜"}], "total": 1}

    def suggest_bioicons(self, args):
        return {"items": [{"name": "cell membrane", "source": "bioicons"}], "total": 1}


class ImageLibraryServiceTest(unittest.TestCase):
    def test_dashboard_reports_image_boundary(self):
        service = ImageLibraryService(catalog_service=FakeImageCatalog())

        result = service.dashboard()

        self.assertEqual(result["boundary"], "image_library")
        self.assertIn("bioicons", result["sources"])

    def test_suggest_assets_merges_elements_and_bioicons(self):
        service = ImageLibraryService(catalog_service=FakeImageCatalog())

        result = service.suggest_assets("细胞膜")

        self.assertEqual(result["query"], "细胞膜")
        self.assertEqual(len(result["items"]), 2)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_platform_services -v
```

Expected: FAIL because `services.image_library_service` does not exist.

- [ ] **Step 3: Implement `ImageLibraryService`**

Create `sci-illust-system/web_app/services/image_library_service.py`:

```python
class ImageLibraryService:
    """图片库聚合服务，负责把图元、Bioicons 和图片资产能力收束到图片库边界。"""

    def __init__(self, catalog_service):
        self.catalog_service = catalog_service

    def dashboard(self):
        return {
            "boundary": "image_library",
            "sources": ["local_files", "mysql_metadata", "bioicons", "image_graph"],
        }

    def suggest_assets(self, query):
        args = {"q": query}
        elements = self.catalog_service.suggest_elements(args)
        bioicons = self.catalog_service.suggest_bioicons(args)
        items = []
        items.extend(elements.get("items", []))
        items.extend(bioicons.get("items", []))
        return {
            "boundary": "image_library",
            "query": query,
            "items": items,
            "total": len(items),
        }
```

- [ ] **Step 4: Export service**

In `services/__init__.py`, add:

```python
from .image_library_service import ImageLibraryService
```

and include `"ImageLibraryService"` in `__all__`.

- [ ] **Step 5: Wire routes in `app.py`**

In `_build_runtime_state()`, instantiate:

```python
image_library_service = ImageLibraryService(catalog_service=catalog_service)
```

Add to runtime state:

```python
"image_library_service": image_library_service,
```

Add routes:

```python
@app.route("/api/image-library/dashboard")
def image_library_dashboard():
    return jsonify(runtime["image_library_service"].dashboard())


@app.route("/api/image-library/suggest")
def image_library_suggest():
    query = request.args.get("q", "")
    return jsonify(runtime["image_library_service"].suggest_assets(query))
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
python -m unittest tests.test_platform_services tests.test_bioicons_library tests.test_element_suggestions -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add sci-illust-system/web_app/services/image_library_service.py sci-illust-system/web_app/services/__init__.py sci-illust-system/web_app/app.py tests/test_platform_services.py
git commit -m "refactor(web): add image library service boundary"
```

---

### Task 4: 应用平台聚合服务

**Files:**
- Create: `sci-illust-system/web_app/services/drawing_app_service.py`
- Modify: `sci-illust-system/web_app/services/__init__.py`
- Modify: `sci-illust-system/web_app/app.py`
- Test: `tests/test_platform_services.py`

**Interfaces:**
- Consumes: `DrawService.workflow(payload)`、`DrawService.draw(payload)`
- Produces: `DrawingApplicationService.create_workflow(payload: dict) -> dict`、`DrawingApplicationService.generate_figure(payload: dict) -> dict`

- [ ] **Step 1: Extend failing test**

Append to `tests/test_platform_services.py`:

```python
from services.drawing_app_service import DrawingApplicationService


class FakeDrawService:
    def workflow(self, payload):
        return {"workflow": {"title": payload["text"]}, "ok": True}

    def draw(self, payload):
        return {"svg": "<svg></svg>", "ok": True}


class DrawingApplicationServiceTest(unittest.TestCase):
    def test_create_workflow_marks_app_boundary(self):
        service = DrawingApplicationService(draw_service=FakeDrawService())

        result = service.create_workflow({"text": "EGFR 通路"})

        self.assertEqual(result["boundary"], "drawing_application")
        self.assertEqual(result["workflow"]["title"], "EGFR 通路")

    def test_generate_figure_marks_app_boundary(self):
        service = DrawingApplicationService(draw_service=FakeDrawService())

        result = service.generate_figure({"text": "EGFR 通路"})

        self.assertEqual(result["boundary"], "drawing_application")
        self.assertIn("<svg", result["svg"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_platform_services -v
```

Expected: FAIL because `services.drawing_app_service` does not exist.

- [ ] **Step 3: Implement `DrawingApplicationService`**

Create `sci-illust-system/web_app/services/drawing_app_service.py`:

```python
class DrawingApplicationService:
    """科研绘图应用平台服务，负责需求、workflow、生成图和导出边界。"""

    def __init__(self, draw_service):
        self.draw_service = draw_service

    def create_workflow(self, payload):
        result = self.draw_service.workflow(payload)
        result["boundary"] = "drawing_application"
        return result

    def generate_figure(self, payload):
        result = self.draw_service.draw(payload)
        result["boundary"] = "drawing_application"
        return result
```

- [ ] **Step 4: Export service**

In `services/__init__.py`, add:

```python
from .drawing_app_service import DrawingApplicationService
```

and include `"DrawingApplicationService"` in `__all__`.

- [ ] **Step 5: Wire routes without breaking existing API**

In `_build_runtime_state()`, instantiate:

```python
drawing_app_service = DrawingApplicationService(draw_service=draw_service)
```

Add to runtime state:

```python
"drawing_app_service": drawing_app_service,
```

Keep existing `/api/workflow` and `/api/draw` routes, but route through the new service:

```python
@app.route("/api/draw", methods=["POST"])
def draw():
    return jsonify(runtime["drawing_app_service"].generate_figure(request.get_json(silent=True) or {}))


@app.route("/api/workflow", methods=["POST"])
def workflow():
    return jsonify(runtime["drawing_app_service"].create_workflow(request.get_json(silent=True) or {}))
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
python -m unittest tests.test_platform_services tests.test_draw_service tests.test_workflow_route tests.test_component_composition -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add sci-illust-system/web_app/services/drawing_app_service.py sci-illust-system/web_app/services/__init__.py sci-illust-system/web_app/app.py tests/test_platform_services.py
git commit -m "refactor(web): add drawing application service boundary"
```

---

### Task 5: MySQL 逻辑库配置抽象

**Files:**
- Modify: `sci-illust-system/web_app/database.py`
- Test: `tests/test_database_config.py`
- Create: `.env.example`

**Interfaces:**
- Consumes: 环境变量 `SCI_MYSQL_HOST`、`SCI_MYSQL_PORT`、`SCI_MYSQL_USER`、`SCI_MYSQL_PASSWORD`、`SCI_TEXT_DB_NAME`、`SCI_IMAGE_DB_NAME`、`SCI_APP_DB_NAME`
- Produces: `logical_database_config() -> dict`

- [ ] **Step 1: Extend failing database config test**

Append to `tests/test_database_config.py`:

```python
    def test_logical_database_config_uses_three_mysql_schemas(self):
        original = {
            key: os.environ.get(key)
            for key in [
                "SCI_MYSQL_HOST",
                "SCI_MYSQL_PORT",
                "SCI_MYSQL_USER",
                "SCI_MYSQL_PASSWORD",
                "SCI_TEXT_DB_NAME",
                "SCI_IMAGE_DB_NAME",
                "SCI_APP_DB_NAME",
            ]
        }
        try:
            os.environ["SCI_MYSQL_HOST"] = "127.0.0.1"
            os.environ["SCI_MYSQL_PORT"] = "3306"
            os.environ["SCI_MYSQL_USER"] = "sci"
            os.environ["SCI_MYSQL_PASSWORD"] = "secret"
            os.environ["SCI_TEXT_DB_NAME"] = "text_db"
            os.environ["SCI_IMAGE_DB_NAME"] = "image_db"
            os.environ["SCI_APP_DB_NAME"] = "app_db"

            config = database_module.logical_database_config()

            self.assertEqual(config["host"], "127.0.0.1")
            self.assertEqual(config["port"], 3306)
            self.assertEqual(config["schemas"]["text"], "text_db")
            self.assertEqual(config["schemas"]["image"], "image_db")
            self.assertEqual(config["schemas"]["app"], "app_db")
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest tests.test_database_config -v
```

Expected: FAIL because `logical_database_config` does not exist.

- [ ] **Step 3: Implement config helper**

In `sci-illust-system/web_app/database.py`, add:

```python
def logical_database_config():
    return {
        "host": os.environ.get("SCI_MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("SCI_MYSQL_PORT", "3306")),
        "user": os.environ.get("SCI_MYSQL_USER", "root"),
        "password": os.environ.get("SCI_MYSQL_PASSWORD", ""),
        "schemas": {
            "text": os.environ.get("SCI_TEXT_DB_NAME", "text_db"),
            "image": os.environ.get("SCI_IMAGE_DB_NAME", "image_db"),
            "app": os.environ.get("SCI_APP_DB_NAME", "app_db"),
        },
    }
```

Do not connect to MySQL in this task.

- [ ] **Step 4: Create `.env.example`**

Create `.env.example`:

```dotenv
SCI_WEBAPP_DB_PATH=sci-illust-system/web_app/data/knowledge.db

SCI_MYSQL_HOST=127.0.0.1
SCI_MYSQL_PORT=3306
SCI_MYSQL_USER=root
SCI_MYSQL_PASSWORD=
SCI_TEXT_DB_NAME=text_db
SCI_IMAGE_DB_NAME=image_db
SCI_APP_DB_NAME=app_db

OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_DEFAULT_MODEL=qwen2.5:3b
```

- [ ] **Step 5: Run focused test**

Run:

```powershell
python -m unittest tests.test_database_config -v
```

Expected: PASS.

- [ ] **Step 6: Run full regression**

Run:

```powershell
$env:BIOICONS_ROOT = Join-Path $env:TEMP 'codex-empty-bioicons-root'
New-Item -ItemType Directory -Force -Path $env:BIOICONS_ROOT | Out-Null
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```powershell
git add sci-illust-system/web_app/database.py tests/test_database_config.py .env.example
git commit -m "chore(config): define logical mysql schemas"
```

---

### Task 6: 页面与接口健康检查

**Files:**
- Modify: `README.md`
- Test: no new test file

**Interfaces:**
- Consumes: Existing `start.bat`、Flask routes
- Produces: documented local verification commands

- [ ] **Step 1: Start local app**

Run:

```powershell
.\start.bat
```

If another terminal is preferred:

```powershell
$repo='D:\ljn-xm\keyanhuitu'
$python='C:\Program Files\Python312\python.exe'
$env:PYTHONPATH="$repo\sci-illust-system\web_app;$repo\sci-illust-system;$repo"
$env:SCI_WEB_MODE='stable'
Start-Process -FilePath $python -ArgumentList @('sci-illust-system\web_app\app.py') -WorkingDirectory $repo -WindowStyle Hidden
```

- [ ] **Step 2: Verify core endpoints**

Run:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5000/" -TimeoutSec 10 | Select-Object StatusCode
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5000/api/dashboard" -TimeoutSec 10 | Select-Object StatusCode
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5000/api/text-library/dashboard" -TimeoutSec 10 | Select-Object StatusCode
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5000/api/image-library/dashboard" -TimeoutSec 10 | Select-Object StatusCode
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5000/api/draw/models" -TimeoutSec 10 | Select-Object StatusCode
```

Expected: each command returns `StatusCode 200`.

- [ ] **Step 3: Document verification**

In `README.md`, add a section:

```markdown
## 平台拆分后的本地检查

当前系统仍是一个 Flask 单体应用，但页面和服务边界已按文本库、图片库、应用平台拆分。

本地启动：

```powershell
.\start.bat
```

关键接口：

```text
GET /api/dashboard
GET /api/text-library/dashboard
GET /api/image-library/dashboard
POST /api/workflow
POST /api/draw
```

回归测试：

```powershell
$env:BIOICONS_ROOT = Join-Path $env:TEMP 'codex-empty-bioicons-root'
New-Item -ItemType Directory -Force -Path $env:BIOICONS_ROOT | Out-Null
python -m unittest discover -s tests -p "test_*.py" -v
```
```

- [ ] **Step 4: Run full regression**

Run:

```powershell
$env:BIOICONS_ROOT = Join-Path $env:TEMP 'codex-empty-bioicons-root'
New-Item -ItemType Directory -Force -Path $env:BIOICONS_ROOT | Out-Null
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add README.md
git commit -m "docs(readme): document platform split checks"
```

---

## Self-Review

Spec coverage:

- 文本库、图片库、应用平台边界：covered by Tasks 1-4.
- 一个 MySQL 实例三个逻辑库：covered by Task 5.
- 生成图作为应用平台核心板块：covered by Task 1 and Task 4.
- 不急于拆独立部署服务：covered by Global Constraints and Task 5.
- 本地验证和回归：covered by Task 6.

- Placeholder scan:

- No unresolved placeholder markers remain.
- Every task has files, interfaces, test command, implementation direction, verification, and commit step.

Type consistency:

- `TextLibraryService.dashboard()`、`ImageLibraryService.dashboard()`、`DrawingApplicationService.create_workflow()` and `DrawingApplicationService.generate_figure()` are defined before route usage.
- New route names use consistent `text-library` and `image-library` URL prefixes.
