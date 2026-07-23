"""科研配图管理系统 - Flask 应用。"""
import os
import sys
from datetime import datetime

BASE_SITE = r"C:\ProgramData\anaconda3\Lib\site-packages"
if os.path.isdir(BASE_SITE) and BASE_SITE not in sys.path:
    sys.path.append(BASE_SITE)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for path in [os.path.dirname(BASE_DIR), os.path.dirname(os.path.dirname(BASE_DIR))]:
    if path not in sys.path:
        sys.path.insert(0, path)

from flask import Flask, jsonify, render_template, request

from database import KnowledgeDatabase
from dify_bridge import DifyBridge
from document_processor import DocumentProcessor
from knowledge_base.element_library import ElementLibrary
from knowledge_base.kb_core import KnowledgeBase

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

kb = KnowledgeBase(
    vocab_path=os.path.join(BASE_DIR, "data", "domain_vocab.json"),
    color_scheme_path=os.path.join(BASE_DIR, "data", "color_schemes", "default_scheme.json"),
)
el = ElementLibrary(kb.vocabulary)
db = KnowledgeDatabase()
dp = DocumentProcessor()
dify = DifyBridge()


def import_builtin():
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


import_builtin()


def _get_ollama_models():
    try:
        from ollama_integration.ollama_client import OllamaClient

        return OllamaClient(timeout=5).list_models()
    except Exception:
        return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard():
    stats = db.stats
    return jsonify({
        "entries": stats["entries"],
        "documents": stats["documents"],
        "vectorized_documents": stats["vectorized_documents"],
        "domains": stats["domains"],
        "kb_terms": kb.stats["total_terms"],
        "kb_vectors": kb.stats["vector_index_size"],
        "ollama_models": _get_ollama_models(),
        "dify_configured": dify.is_configured,
    })


@app.route("/api/entries")
def list_entries():
    domain = request.args.get("domain", "")
    search = request.args.get("search", "")
    entries, total = db.list_entries(domain=domain, search=search)
    return jsonify({"entries": entries, "total": total})


@app.route("/api/entries", methods=["POST"])
def add_entry():
    data = request.json or {}
    ok = db.add_entry(
        name=data["name"],
        english=data.get("english", ""),
        domain=data.get("domain", ""),
        category=data.get("category", ""),
        shape=data.get("shape", ""),
        color_scheme=data.get("color_scheme", []),
        tags=data.get("tags", []),
        description=data.get("description", ""),
    )
    return jsonify({"success": ok})


@app.route("/api/entries/<int:eid>", methods=["PUT", "DELETE"])
def update_or_delete_entry(eid):
    if request.method == "DELETE":
        db.delete_entry(eid)
        return jsonify({"success": True})

    db.update_entry(eid, **(request.json or {}))
    return jsonify({"success": True})


@app.route("/api/search")
def search_kb():
    return jsonify({"results": kb.query(request.args.get("q", ""), top_k=10)})


@app.route("/api/elements/suggest")
def suggest_elements():
    items = el.suggest(request.args.get("text", ""), top_k=8)
    return jsonify({"elements": [item.to_dict() for item in items]})


@app.route("/api/document/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "未上传文件"})

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "文件名为空"})

    path = os.path.join(dp.upload_dir, file.filename)
    file.save(path)
    return jsonify(dp.process_file(path, file.filename))


@app.route("/api/documents")
def list_documents():
    return jsonify({"documents": db.list_documents()})


@app.route("/api/documents/<int:did>", methods=["DELETE"])
def delete_document(did):
    db.delete_document(did)
    return jsonify({"success": True})


@app.route("/api/dify/status")
def dify_status():
    return jsonify(dify.test_connection())


@app.route("/api/dify/configure", methods=["POST"])
def dify_configure():
    global dify

    data = request.json or {}
    dify = DifyBridge(api_key=data.get("api_key"), base_url=data.get("base_url"))
    return jsonify(dify.test_connection())


@app.route("/api/ollama/status")
def ollama_status():
    models = _get_ollama_models()
    return jsonify({"running": len(models) > 0, "models": models})


@app.route("/api/draw/models")
def draw_models():
    return jsonify({"models": _get_ollama_models()})


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
    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "请输入绘图需求"})

    figure_type = data.get("figure_type", "")
    style = data.get("style", "")
    layout = data.get("layout", "")
    model = data.get("model", "")
    canvas_width = int(data.get("canvas_width", 900))
    canvas_height = int(data.get("canvas_height", 600))

    if not figure_type or not style:
        from orchestrator.text_analyzer import RequirementAnalyzer

        analysis = RequirementAnalyzer(kb).analyze(text)
        figure_type = figure_type or analysis["figure_type"]
        style = style or analysis["style"]

    from drawing.layout_engine import LayoutType
    from orchestrator.pipeline import SciIllustPipeline

    layout_map = {
        "force_directed": LayoutType.FORCE_DIRECTED,
        "hierarchical": LayoutType.HIERARCHICAL,
        "grid": LayoutType.GRID,
        "radial": LayoutType.RADIAL,
    }
    pipeline = SciIllustPipeline()
    if model:
        result = pipeline.process_components(
            text,
            model=model,
            style_name=style,
            layout=layout or "hierarchical",
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            auto_render=True,
        )
    else:
        result = pipeline.process(
            text,
            figure_type=figure_type,
            style_name=style,
            layout_type=layout_map.get(layout) if layout else None,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            auto_render=True,
        )

    analysis = result.get("analysis", {})
    elements = result.get("elements", [])
    relations = result.get("relations", [])

    if result.get("mode") == "components":
        element_list = [
            {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "shape": item.get("image_key", ""),
                "caption": item.get("caption", ""),
            }
            for item in result.get("components", [])[:15]
        ]
        relation_list = [
            {
                "source": item.get("source", ""),
                "target": item.get("target", ""),
                "type": item.get("type", "arrow"),
                "label": item.get("label", ""),
                "directed": True,
            }
            for item in result.get("connections", [])[:12]
        ]
    else:
        element_list = [
            {"id": item.get("name", ""), "name": item.get("name", ""), "shape": item.get("shape", "")}
            for item in elements[:15]
        ]
        relation_list = []
        for relation in relations[:10]:
            source = getattr(relation, "source", "")
            target = getattr(relation, "target", "")
            relation_type = getattr(relation, "relation_type", "connected_to")
            directed = getattr(relation, "directed", False)
            relation_list.append({
                "source": source,
                "target": target,
                "type": relation_type,
                "directed": directed,
            })

    return jsonify({
        "success": True,
        "svg": result.get("svg", ""),
        "analysis": {
            "domain": analysis.get("domain", ""),
            "figure_type": figure_type,
            "style": style,
            "canvas": f"{canvas_width}x{canvas_height}",
        },
        "elements": element_list,
        "relations": relation_list,
        "summary": analysis.get("analysis_summary", ""),
        "mode": result.get("mode", "elements"),
        "component_plan": result.get("component_plan"),
        "model_used": model or "keyword",
        "timestamp": str(datetime.now()),
    })


@app.route("/api/query", methods=["POST"])
def query_llm():
    data = request.json or {}
    text = data.get("text", "")
    if data.get("use_dify") and dify.is_configured:
        response = dify.chat(text)
        if response:
            return jsonify({"response": response, "source": "dify"})

    try:
        from ollama_integration.ollama_client import OllamaClient

        client = OllamaClient(timeout=60)
        response = client.chat(
            [
                {"role": "system", "content": "你是科研绘图专家。"},
                {"role": "user", "content": text},
            ],
            model=data.get("model", "qwen3.5:4b"),
        )
        return jsonify({"response": response or "模型无响应", "source": "ollama"})
    except Exception as exc:
        return jsonify({"response": f"调用失败: {exc}", "source": "error"})


if __name__ == "__main__":
    print("启动: http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
