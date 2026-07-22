import os
from .text_analyzer import RequirementAnalyzer
from knowledge_base.kb_core import KnowledgeBase

class SciIllustPipeline:
    def __init__(self):
        self.kb = KnowledgeBase()
    def process(self, text, figure_type="", style_name="", layout_type=None,
                canvas_width=900, canvas_height=600, auto_render=True):
        analysis = RequirementAnalyzer(self.kb).analyze(text)
        els = analysis.get("elements", [])
        names = [e["name"] for e in els[:8]]
        y = canvas_height // 2
        svg = "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 " + str(canvas_width) + " " + str(canvas_height) + "\" width=\"600\" height=\"400\"><rect width=\"100%\" height=\"100%\" fill=\"white\" rx=\"4\"/><text x=\"30\" y=\"30\" font-size=\"16\" fill=\"#333\" font-weight=\"bold\">" + analysis.get("analysis_summary","") + "</text>"
        for i, name in enumerate(names):
            svg += "<rect x=\"" + str(30 + i*100) + "\" y=\"60\" width=\"80\" height=\"40\" rx=\"6\" fill=\"#e3f2fd\" stroke=\"#1976d2\"/><text x=\"" + str(70 + i*100) + "\" y=\"85\" text-anchor=\"middle\" font-size=\"12\" fill=\"#333\">" + name + "</text>"
        svg += "</svg>"
        return {"status": "completed", "svg": svg, "elements": els,
                "relations": analysis.get("relations", []), "analysis": analysis,
                "figure_info": {"elements": len(els), "figure_type": figure_type}}
    
    def compose_scene(self, text, width=1000, height=700):
        """Knowledge Graph -> SVG scene"""
        try:
            from drawing.scene_composer import SceneComposer
            from knowledge_base.knowledge_graph import ScientificGraph
            return SceneComposer(ScientificGraph()).compose(text, width, height)
        except Exception as e:
            return "<svg><text x=\"10\" y=\"20\">Error: " + str(e) + "</text></svg>"
def process_and_save(self, text, path, **kw):
        r = self.process(text, **kw)
        with open(path, "w", encoding="utf-8") as f:
            f.write(r.get("svg", ""))
        return path
