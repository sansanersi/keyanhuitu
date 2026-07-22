import re
class RequirementAnalyzer:
    def __init__(self, kb=None):
        self.kb = kb
    def analyze(self, text):
        elements = []
        if self.kb:
            for r in self.kb.query(text, top_k=8):
                elements.append({"name": r["term"], "english": r["metadata"]["english"],
                    "shape": r["metadata"]["shape"], "color_scheme": r["metadata"]["color_scheme"],
                    "type": r["metadata"]["type"], "domain": r["metadata"]["domain"],
                    "confidence": r["score"]})
        domain = elements[0]["domain"] if elements else "biology"
        return {"domain": domain, "figure_type": "schematic_diagram", "style": "science",
                "view_type": "2d_top", "elements": elements, "relations": [],
                "analysis_summary": "学科: " + domain + " | 元素: " + str(len(elements)) + "个"}
