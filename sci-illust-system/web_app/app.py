"""科研配图管理系统 — 单文件 Flask 应用"""
import os, sys, json, re
from datetime import datetime

# 兼容 sci conda 环境：从 base anaconda3 加载 flask
BASE_SITE = r"C:\ProgramData\anaconda3\Lib\site-packages"
if not os.path.exists(BASE_SITE):
    BASE_SITE = r"C:\ProgramData\anaconda3\Lib\site-packages"
if os.path.isdir(BASE_SITE) and BASE_SITE not in sys.path:
    sys.path.append(BASE_SITE)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for p in [os.path.dirname(BASE_DIR), os.path.dirname(os.path.dirname(BASE_DIR))]:
    if p not in sys.path:
        sys.path.insert(0, p)

from flask import Flask, render_template, request, jsonify
from database import KnowledgeDatabase
from document_processor import DocumentProcessor
from dify_bridge import DifyBridge
from knowledge_base.kb_core import KnowledgeBase
from knowledge_base.element_library import ElementLibrary

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

kb = KnowledgeBase(vocab_path=os.path.join(BASE_DIR, "data", "domain_vocab.json"),
                   color_scheme_path=os.path.join(BASE_DIR, "data", "color_schemes", "default_scheme.json"))
el = ElementLibrary(kb.vocabulary)
db = KnowledgeDatabase()
dp = DocumentProcessor()
dify = DifyBridge()

def import_builtin():
    if db.stats["entries"] == 0:
        for t in kb.vocabulary.all_terms:
            m = kb.get_term(t)
            if m:
                db.add_entry(name=t, english=m["english"], domain=m["domain"],
                             category=m["category"], shape=m["shape"],
                             color_scheme=m["color_scheme"], tags=m["tags"])
import_builtin()

def _get_ollama_models():
    try:
        from ollama_integration.ollama_client import OllamaClient
        return OllamaClient(timeout=5).list_models()
    except Exception:
        return []

# ─── Routes ───
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/dashboard")
def dashboard():
    s = db.stats
    return jsonify({"entries": s["entries"], "documents": s["documents"],
        "vectorized_documents": s["vectorized_documents"],
        "domains": s["domains"], "kb_terms": kb.stats["total_terms"],
        "kb_vectors": kb.stats["vector_index_size"],
        "ollama_models": _get_ollama_models(),
        "dify_configured": dify.is_configured})

@app.route("/api/entries")
def list_entries():
    domain = request.args.get("domain", "")
    search = request.args.get("search", "")
    entries, total = db.list_entries(domain=domain, search=search)
    return jsonify({"entries": entries, "total": total})

@app.route("/api/entries", methods=["POST"])
def add_entry():
    d = request.json
    ok = db.add_entry(name=d["name"], english=d.get("english",""),
        domain=d.get("domain",""), category=d.get("category",""),
        shape=d.get("shape",""), color_scheme=d.get("color_scheme",[]),
        tags=d.get("tags",[]), description=d.get("description",""))
    return jsonify({"success": ok})

@app.route("/api/entries/<int:eid>", methods=["PUT", "DELETE"])
def update_or_delete_entry(eid):
    if request.method == "DELETE":
        db.delete_entry(eid)
        return jsonify({"success": True})
    d = request.json
    db.update_entry(eid, **d)
    return jsonify({"success": True})

@app.route("/api/search")
def search_kb():
    return jsonify({"results": kb.query(request.args.get("q",""), top_k=10)})

@app.route("/api/elements/suggest")
def suggest_elements():
    items = el.suggest(request.args.get("text",""), top_k=8)
    return jsonify({"elements": [t.to_dict() for t in items]})

@app.route("/api/document/upload", methods=["POST"])
def upload_document():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "no file"})
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"success": False, "error": "empty filename"})
    path = os.path.join(dp.upload_dir, f.filename)
    f.save(path)
    return jsonify(dp.process_file(path, f.filename))

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
    d = request.json
    dify = DifyBridge(api_key=d.get("api_key"), base_url=d.get("base_url"))
    return jsonify(dify.test_connection())

@app.route("/api/ollama/status")
def ollama_status():
    m = _get_ollama_models()
    return jsonify({"running": len(m) > 0, "models": m})

# ─── Draw Routes ───
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
    return jsonify({"layouts": [lt.value for lt in LayoutType]})

@app.route("/api/draw/styles")
def draw_styles():
    from drawing.style_engine import StyleEngine
    return jsonify({"styles": StyleEngine().list_schemes()})

@app.route("/api/draw", methods=["POST"])
def draw():
    d = request.json
    text = d.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "请输入需求"})
    ft = d.get("figure_type", "")
    st = d.get("style", "")
    lt = d.get("layout", "")
    mn = d.get("model", "")
    cw = int(d.get("canvas_width", 900))
    ch = int(d.get("canvas_height", 600))

    if not ft or not st:
        from orchestrator.text_analyzer import RequirementAnalyzer
        a = RequirementAnalyzer(kb).analyze(text)
        ft = ft or a["figure_type"]
        st = st or a["style"]

    from drawing.layout_engine import LayoutType
    lm = {"force_directed": LayoutType.FORCE_DIRECTED, "hierarchical": LayoutType.HIERARCHICAL,
          "grid": LayoutType.GRID, "radial": LayoutType.RADIAL}

    from orchestrator.pipeline import SciIllustPipeline
    p = SciIllustPipeline()
    r = p.process(text, figure_type=ft, style_name=st,
                  layout_type=lm.get(lt) if lt else None,
                  canvas_width=cw, canvas_height=ch, auto_render=True)

    ana = r.get("analysis", {})
    els = r.get("elements", [])
    rels = r.get("relations", [])

    elist = [{"id":e.get("name",""),"name":e.get("name",""),"shape":e.get("shape","")} for e in els[:15]]
    rlist = []
    for rel in rels[:10]:
        try:
            si = int(rel.source.replace("el_","")) if rel.source.startswith("el_") else 0
            ti = int(rel.target.replace("el_","")) if rel.target.startswith("el_") else 0
            sn = els[si].name if si < len(els) else rel.source
            tn = els[ti].name if ti < len(els) else rel.target
        except (ValueError, IndexError):
            sn, tn = rel.source, rel.target
        rlist.append({"source": sn, "target": tn, "type": rel.relation_type, "directed": rel.directed})

    return jsonify({
        "success": True,
        "svg": r.get("svg", ""),
        "analysis": {"domain": ana.get("domain",""), "figure_type": ft, "style": st, "canvas": f"{cw}x{ch}"},
        "elements": elist, "relations": rlist,
        "summary": ana.get("analysis_summary",""),
        "model_used": mn or "keyword",
        "timestamp": str(datetime.now())
    })

@app.route("/api/query", methods=["POST"])
def query_llm():
    d = request.json
    text = d.get("text", "")
    if d.get("use_dify") and dify.is_configured:
        r = dify.chat(text)
        if r:
            return jsonify({"response": r, "source": "dify"})
    try:
        from ollama_integration.ollama_client import OllamaClient
        c = OllamaClient(timeout=60)
        r = c.chat([{"role":"system","content":"你是科研绘图专家。"},{"role":"user","content":text}],
                   model=d.get("model","qwen3.5:4b"))
        return jsonify({"response": r or "模型无响应", "source": "ollama"})
    except Exception as e:
        return jsonify({"response": f"调用失败: {e}", "source": "error"})

if __name__ == "__main__":
    print("启动: http://127.0.0.1:5000")
    app.run(debug=True, host="127.0.0.1", port=5000)
