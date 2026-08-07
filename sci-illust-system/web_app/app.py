"""科研配图管理系统 Web 应用。"""

import os
import sys

BASE_SITE = r"C:\ProgramData\anaconda3\Lib\site-packages"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _configure_import_paths():
    if os.path.isdir(BASE_SITE) and BASE_SITE not in sys.path:
        sys.path.append(BASE_SITE)

    for path in (os.path.dirname(BASE_DIR), os.path.dirname(os.path.dirname(BASE_DIR))):
        if path not in sys.path:
            sys.path.insert(0, path)


_configure_import_paths()

from flask import Flask, jsonify, render_template, request

try:
    from .database import KnowledgeDatabase
    from .document_processor import DocumentProcessor
    from .services import (
        CatalogService,
        DocumentService,
        DrawingApplicationService,
        DrawService,
        ImageLibraryService,
        SearchService,
        SystemService,
        TextLibraryService,
    )
except ImportError:
    from database import KnowledgeDatabase
    from document_processor import DocumentProcessor
    from services import (
        CatalogService,
        DocumentService,
        DrawingApplicationService,
        DrawService,
        ImageLibraryService,
        SearchService,
        SystemService,
        TextLibraryService,
    )

from knowledge_base.bioicons_library import BioiconsLibrary
from knowledge_base.element_library import ElementLibrary
from knowledge_base.kb_core import KnowledgeBase
from orchestrator.asset_resolver import AssetResolver
from text_kb.graphrag_manager import GraphRAGTextKBManager

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

FOCUS_DOMAIN = os.environ.get("SCI_FOCUS_DOMAIN", "biology")
CORPUS_PATHS = [
    os.path.join(BASE_DIR, "data", "corpus", FOCUS_DOMAIN),
    os.path.join(BASE_DIR, "data", "corpus"),
]


def _build_runtime_state():
    knowledge_base = KnowledgeBase(
        vocab_path=os.path.join(BASE_DIR, "data", "domain_vocab.json"),
        color_scheme_path=os.path.join(BASE_DIR, "data", "color_schemes", "default_scheme.json"),
        focus_domain=FOCUS_DOMAIN,
        corpus_paths=CORPUS_PATHS,
    )
    return {
        "kb": knowledge_base,
        "el": ElementLibrary(knowledge_base.vocabulary),
        "db": KnowledgeDatabase(),
        "dp": DocumentProcessor(),
        "text_kb": GraphRAGTextKBManager(focus_domain=FOCUS_DOMAIN),
        "bioicons": BioiconsLibrary(os.environ.get("BIOICONS_ROOT", r"E:\AI\bioicons-main")),
    }


RUNTIME = _build_runtime_state()
kb = RUNTIME["kb"]
el = RUNTIME["el"]
db = RUNTIME["db"]
dp = RUNTIME["dp"]
text_kb = RUNTIME["text_kb"]
bioicons = RUNTIME["bioicons"]


def _import_builtin_entries():
    if db.stats["entries"] != 0:
        return

    for term in kb.vocabulary.all_terms:
        metadata = kb.get_term(term)
        if metadata:
            db.add_entry(
                name=term,
                english=metadata["english"],
                domain=metadata["domain"],
                category=metadata["category"],
                shape=metadata["shape"],
                color_scheme=metadata["color_scheme"],
                tags=metadata["tags"],
            )


def _ollama_base_url():
    return db.get_setting("ollama_base_url", "http://127.0.0.1:11434")


def _ollama_default_model():
    return db.get_setting("ollama_default_model", "qwen3.5:4b")


def _ollama_client(timeout=5):
    from ollama_integration.ollama_client import OllamaClient

    return OllamaClient(base_url=_ollama_base_url(), default_model=_ollama_default_model(), timeout=timeout)


def _normalize_ollama_base_url(base_url):
    url = (base_url or "").strip().rstrip("/")
    if url.endswith("/api"):
        return url[:-4]
    if url.endswith("/v1"):
        return url[:-3]
    return url or "http://127.0.0.1:11434"


def _get_ollama_models():
    try:
        return _ollama_client(timeout=5).list_models()
    except Exception:
        return []


def _web_mode():
    return os.environ.get("SCI_WEB_MODE", "stable").strip().lower() or "stable"


document_service = DocumentService(lambda: db, lambda: dp, lambda: text_kb, FOCUS_DOMAIN)
search_service = SearchService(kb, text_kb, FOCUS_DOMAIN)
catalog_service = CatalogService(lambda: db, lambda: kb, lambda: el, lambda: bioicons, FOCUS_DOMAIN)
text_library_service = TextLibraryService(
    catalog_service=catalog_service,
    document_service=document_service,
    search_service=search_service,
)
image_library_service = ImageLibraryService(catalog_service=catalog_service)
draw_service = DrawService(
    knowledge_base=kb,
    pipeline_factory=lambda: __import__("orchestrator.pipeline", fromlist=["SciIllustPipeline"]).SciIllustPipeline(),
    asset_resolver_factory=lambda: AssetResolver(element_library=el, bioicons=bioicons),
)
drawing_app_service = DrawingApplicationService(draw_service=draw_service)
system_service = SystemService(
    database_getter=lambda: db,
    knowledge_base=kb,
    text_kb_manager=text_kb,
    bioicons_library=bioicons,
    focus_domain=FOCUS_DOMAIN,
    sync_uploaded_documents=lambda: document_service.sync_uploaded_documents(),
    get_ollama_models=lambda: _get_ollama_models(),
    web_mode_getter=_web_mode,
)

_import_builtin_entries()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return ("", 204)


@app.route("/api/dashboard")
def dashboard():
    return jsonify(system_service.dashboard())


@app.route("/api/text-library/dashboard")
def text_library_dashboard():
    return jsonify(text_library_service.dashboard())


@app.route("/api/image-library/dashboard")
def image_library_dashboard():
    return jsonify(image_library_service.dashboard())


@app.route("/api/image-library/suggest")
def image_library_suggest():
    query = request.args.get("q", request.args.get("text", ""))
    top_k = int(request.args.get("top_k", 8))
    return jsonify(image_library_service.suggest_assets(query, top_k=top_k))


@app.route("/api/entries")
def list_entries():
    domain = request.args.get("domain", "")
    search = request.args.get("search", "")
    return jsonify(catalog_service.list_entries(domain=domain, search=search))


@app.route("/api/entries", methods=["POST"])
def add_entry():
    return jsonify(catalog_service.add_entry(request.json or {}))


@app.route("/api/entries/<int:eid>", methods=["PUT", "DELETE"])
def update_or_delete_entry(eid):
    if request.method == "DELETE":
        return jsonify(catalog_service.delete_entry(eid))

    return jsonify(catalog_service.update_entry(eid, request.json or {}))


@app.route("/api/search")
def search_kb():
    query = request.args.get("q", "").strip()
    return jsonify(search_service.search(query))


@app.route("/api/domain/status")
def domain_status():
    return jsonify(catalog_service.domain_status())


@app.route("/api/elements/suggest")
def suggest_elements():
    text = request.args.get("text", "")
    return jsonify(catalog_service.suggest_elements(text, top_k=8))


@app.route("/api/bioicons/status")
def bioicons_status():
    return jsonify(catalog_service.bioicons_status())


@app.route("/api/bioicons/suggest")
def suggest_bioicons():
    text = request.args.get("text", "")
    top_k = int(request.args.get("top_k", 8))
    return jsonify(catalog_service.suggest_bioicons(text, top_k=top_k))


@app.route("/api/document/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "未上传文件"})

    result = document_service.upload_document(request.files["file"])
    if not result.get("success") and result.get("error") == "empty_filename":
        return jsonify({"success": False, "error": "文件名为空"})
    return jsonify(result)


@app.route("/api/documents")
def list_documents():
    return jsonify(document_service.list_documents())


@app.route("/api/text-kb/status")
def text_kb_status():
    return jsonify(document_service.text_kb_status())


@app.route("/api/text-kb/init", methods=["POST"])
def init_text_kb():
    data = request.json or {}
    initialize_cli = bool(data.get("initialize_cli", False))
    force = bool(data.get("force", False))
    try:
        result = document_service.init_text_kb(initialize_cli=initialize_cli, force=force)
        return jsonify({"success": True, **result})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)})


@app.route("/api/documents/<int:did>", methods=["DELETE"])
def delete_document(did):
    db.delete_document(did)
    return jsonify({"success": True})


@app.route("/api/ollama/status")
def ollama_status():
    return jsonify(system_service.ollama_status(_ollama_base_url(), _ollama_default_model()))


@app.route("/api/ollama/config", methods=["GET", "POST"])
def ollama_config():
    if request.method == "GET":
        return jsonify(system_service.ollama_config(_ollama_base_url(), _ollama_default_model()))

    data = request.json or {}
    base_url = _normalize_ollama_base_url(data.get("base_url", ""))
    default_model = data.get("default_model", "").strip()
    system_service.update_ollama_config(base_url=base_url, default_model=default_model)
    return jsonify({"success": True, **system_service.ollama_config(_ollama_base_url(), _ollama_default_model())})


@app.route("/api/draw/models")
def draw_models():
    return jsonify(system_service.draw_models(_ollama_base_url(), _ollama_default_model()))


@app.route("/api/draw/shapes")
def draw_shapes():
    from drawing.element_gen import SVGElementGenerator

    return jsonify({"shapes": SVGElementGenerator().list_available_shapes()})


@app.route("/api/draw/layouts")
def draw_layouts():
    from drawing.layout_engine import LayoutType

    return jsonify({"layouts": [layout.value for layout in LayoutType]})


@app.route("/api/draw/styles")
def draw_styles():
    from drawing.style_engine import StyleEngine

    return jsonify({"styles": StyleEngine().list_schemes()})


@app.route("/api/draw", methods=["POST"])
def draw():
    response = drawing_app_service.generate_figure(request.json or {})
    if not response.get("success") and response.get("error") == "missing_text":
        return jsonify({"success": False, "error": "请输入绘图需求"})
    return jsonify(response)


@app.route("/api/workflow", methods=["POST"])
def workflow():
    response = drawing_app_service.create_workflow(request.json or {})
    if not response.get("success") and response.get("error") == "missing_text":
        return jsonify({"success": False, "error": "请输入绘图需求"})
    return jsonify(response)


@app.route("/api/query", methods=["POST"])
def query_llm():
    data = request.json or {}
    text = data.get("text", "")

    try:
        return jsonify(
            system_service.query_llm(
                text=text,
                model=data.get("model", ""),
                base_url=_ollama_base_url(),
                default_model=_ollama_default_model(),
            )
        )
    except Exception as exc:
        return jsonify({"response": f"调用失败: {exc}", "source": "error"})


def run_web_app():
    host = "127.0.0.1"
    port = 5000
    mode = _web_mode()
    print(f"Web service: http://{host}:{port} (mode={mode})")

    if mode == "dev":
        app.run(debug=True, host=host, port=port, use_reloader=True)
        return

    try:
        from waitress import serve

        serve(app, host=host, port=port)
    except Exception:
        app.run(debug=False, host=host, port=port, use_reloader=False)


if __name__ == "__main__":
    print("启动: http://127.0.0.1:5000")
    run_web_app()
