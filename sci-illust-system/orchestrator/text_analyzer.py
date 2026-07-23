import re


class RequirementAnalyzer:
    RELATION_KEYWORDS = {
        "activate": "activates",
        "activates": "activates",
        "activated": "activates",
        "激活": "activates",
        "bind": "binds",
        "binds": "binds",
        "binding": "binds",
        "结合": "binds",
        "inhibit": "inhibits",
        "inhibits": "inhibits",
        "抑制": "inhibits",
        "phosphorylate": "phosphorylates",
        "phosphorylates": "phosphorylates",
        "磷酸化": "phosphorylates",
        "传递": "transfers_to",
    }

    def __init__(self, kb=None):
        self.kb = kb

    def analyze(self, text):
        elements = self._extract_elements(text)
        relations = self._extract_relations(text, elements)
        domain = elements[0]["domain"] if elements else self._guess_domain(text)
        figure_type = self._guess_figure_type(text, relations)
        layout = self._suggest_layout(figure_type, relations)
        style = "science"

        return {
            "domain": domain,
            "figure_type": figure_type,
            "elements": elements,
            "relations": relations,
            "layout": layout,
            "style": style,
            "view_type": "2d_top",
            "analysis_summary": "学科: " + domain + " | 元素: " + str(len(elements)) + " 个",
        }

    def _extract_elements(self, text):
        elements = []
        seen = set()

        if self.kb:
            for result in self.kb.query(text, top_k=8):
                metadata = result["metadata"]
                name = result["term"]
                if name in seen:
                    continue
                elements.append({
                    "id": self._element_id(len(elements)),
                    "name": name,
                    "english": metadata.get("english", ""),
                    "shape": metadata.get("shape", "rounded_rect"),
                    "color_scheme": metadata.get("color_scheme", ["#3498DB"]),
                    "type": metadata.get("type", "entity"),
                    "domain": metadata.get("domain", "biology"),
                    "confidence": result.get("score", 0),
                })
                seen.add(name)

        for name in self._fallback_terms(text):
            if name in seen:
                continue
            elements.append({
                "id": self._element_id(len(elements)),
                "name": name,
                "english": name,
                "shape": self._shape_for_name(name),
                "color_scheme": self._color_for_index(len(elements)),
                "type": "entity",
                "domain": self._guess_domain(name),
                "confidence": 0.5,
            })
            seen.add(name)
            if len(elements) >= 8:
                break

        return elements[:8]

    def _extract_relations(self, text, elements):
        if len(elements) < 2:
            return []

        relation_type = "connected_to"
        lowered = text.lower()
        for keyword, mapped in self.RELATION_KEYWORDS.items():
            if keyword.lower() in lowered or keyword in text:
                relation_type = mapped
                break

        relations = []
        for index in range(len(elements) - 1):
            relations.append({
                "source": elements[index]["id"],
                "target": elements[index + 1]["id"],
                "type": relation_type,
                "relation_type": relation_type,
                "directed": True,
                "label": self._relation_label(relation_type),
            })
        return relations

    def _fallback_terms(self, text):
        latin = re.findall(r"\b[A-Z][A-Z0-9-]{1,}\b", text)
        chinese = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
        stopwords = {"激活", "结合", "传递", "引发", "并将", "然后"}
        terms = []
        for item in latin + chinese:
            if item not in stopwords and item not in terms:
                terms.append(item)
        return terms

    def _guess_domain(self, text):
        if re.search(r"cell|gene|protein|EGF|EGFR|RAS|DNA|RNA|细胞|基因|受体|激酶", text, re.I):
            return "biology"
        if re.search(r"reaction|catalyst|molecule|反应|催化|分子", text, re.I):
            return "chemistry"
        if re.search(r"nano|crystal|material|纳米|晶体|材料", text, re.I):
            return "materials"
        if re.search(r"pollution|water|soil|污染|水体|土壤", text, re.I):
            return "environment"
        return "biology"

    def _guess_figure_type(self, text, relations):
        if relations and re.search(r"pathway|signal|cascade|通路|信号|级联", text, re.I):
            return "pathway_diagram"
        if relations:
            return "mechanism_diagram"
        return "schematic_diagram"

    def _suggest_layout(self, figure_type, relations):
        if figure_type in ("pathway_diagram", "mechanism_diagram") or relations:
            return "hierarchical"
        return "grid"

    def _shape_for_name(self, name):
        if re.search(r"receptor|EGFR|受体", name, re.I):
            return "transmembrane"
        if re.search(r"DNA|RNA|gene|基因", name, re.I):
            return "double_helix"
        if re.search(r"cell|细胞", name, re.I):
            return "circle"
        return "rounded_rect"

    def _color_for_index(self, index):
        colors = [
            ["#4A90D9", "#2F6FBA"],
            ["#E67E22", "#D35400"],
            ["#27AE60", "#1E8449"],
            ["#8E44AD", "#71368A"],
            ["#C0392B", "#922B21"],
        ]
        return colors[index % len(colors)]

    def _relation_label(self, relation_type):
        labels = {
            "activates": "激活",
            "binds": "结合",
            "inhibits": "抑制",
            "phosphorylates": "磷酸化",
            "transfers_to": "传递",
            "connected_to": "关联",
        }
        return labels.get(relation_type, relation_type)

    def _element_id(self, index):
        return "el_" + str(index)
