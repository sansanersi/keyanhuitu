from drawing.layout_engine import LayoutType
from drawing.component_composer import ComponentComposer
from drawing.renderer import FigureElement, FigureRelation, ScientificIllustration
from knowledge_base.kb_core import KnowledgeBase
from orchestrator.component_planner import ComponentPlanner
from orchestrator.text_analyzer import RequirementAnalyzer


class SciIllustPipeline:
    def __init__(self, kb=None):
        self.kb = kb or KnowledgeBase()

    def process(
        self,
        text,
        figure_type="",
        style_name="",
        layout_type=None,
        canvas_width=900,
        canvas_height=600,
        auto_render=True,
    ):
        analysis = RequirementAnalyzer(self.kb).analyze(text)
        figure_type = figure_type or analysis.get("figure_type", "schematic_diagram")
        style_name = style_name or analysis.get("style", "science")
        layout_type = layout_type or self._layout_type(analysis.get("layout", "grid"))
        analysis["figure_type"] = figure_type
        analysis["style"] = style_name
        analysis["layout"] = layout_type.value

        figure = ScientificIllustration()
        figure.setup_canvas(canvas_width, canvas_height)
        figure.set_figure_type(figure_type)
        figure.set_style(style_name)
        figure.set_title(analysis.get("analysis_summary", ""))

        elements = [self._to_figure_element(item, index) for index, item in enumerate(analysis.get("elements", []))]
        relations = [self._to_figure_relation(item) for item in analysis.get("relations", [])]
        figure.add_elements(elements)
        figure.add_relations(relations)

        svg = figure.render(layout_type) if auto_render else ""
        return {
            "status": "completed",
            "svg": svg,
            "elements": analysis.get("elements", []),
            "relations": relations,
            "analysis": analysis,
            "figure_info": figure.info,
        }

    def process_and_save(self, text, path, **kwargs):
        result = self.process(text, **kwargs)
        with open(path, "w", encoding="utf-8") as f:
            f.write(result.get("svg", ""))
        return path

    def process_components(
        self,
        text,
        model="",
        style_name="science",
        layout="",
        canvas_width=900,
        canvas_height=600,
        auto_render=True,
    ):
        planner = ComponentPlanner(self.kb)
        plan = planner.plan(text, model=model, style=style_name, layout=layout)
        svg = ComponentComposer().render(plan, width=canvas_width, height=canvas_height) if auto_render else ""
        return {
            "status": "completed",
            "mode": "components",
            "svg": svg,
            "component_plan": plan,
            "components": plan.get("components", []),
            "connections": plan.get("connections", []),
            "analysis": {
                "domain": self._domain_from_components(plan.get("components", [])),
                "figure_type": "component_diagram",
                "layout": plan.get("layout", layout or "hierarchical"),
                "style": plan.get("style", style_name or "science"),
                "source": plan.get("source", "ollama" if model else "fallback"),
            },
            "figure_info": {
                "elements": len(plan.get("components", [])),
                "relations": len(plan.get("connections", [])),
                "figure_type": "component_diagram",
                "style": plan.get("style", style_name or "science"),
                "canvas": str(canvas_width) + "x" + str(canvas_height),
            },
        }

    def compose_scene(self, text, width=1000, height=700):
        """Knowledge Graph -> SVG scene."""
        try:
            from drawing.scene_composer import SceneComposer
            from knowledge_base.knowledge_graph import ScientificGraph

            return SceneComposer(ScientificGraph()).compose(text, width, height)
        except Exception as exc:
            return "<svg><text x=\"10\" y=\"20\">Error: " + str(exc) + "</text></svg>"

    def _to_figure_element(self, item, index):
        element_id = item.get("id") or "el_" + str(index)
        return FigureElement(
            eid=element_id,
            name=item.get("name", element_id),
            shape=item.get("shape", "rounded_rect"),
            color_scheme=item.get("color_scheme") or ["#3498DB"],
            width=self._element_width(item),
            height=self._element_height(item),
            label=item.get("name", element_id),
        )

    def _to_figure_relation(self, item):
        relation_type = item.get("relation_type") or item.get("type") or "connected_to"
        return FigureRelation(
            source=item.get("source", ""),
            target=item.get("target", ""),
            relation_type=relation_type,
            directed=item.get("directed", True),
            label=item.get("label", ""),
        )

    def _layout_type(self, value):
        if isinstance(value, LayoutType):
            return value
        for layout_type in LayoutType:
            if layout_type.value == value:
                return layout_type
        return LayoutType.GRID

    def _element_width(self, item):
        shape = item.get("shape", "")
        if shape in ("lipid_bilayer", "tube_cylinder"):
            return 120
        if shape in ("double_helix", "transmembrane"):
            return 76
        return 84

    def _element_height(self, item):
        shape = item.get("shape", "")
        if shape in ("lipid_bilayer",):
            return 48
        if shape in ("transmembrane", "double_helix"):
            return 76
        return 58

    def _domain_from_components(self, components):
        joined = " ".join([component.get("name", "") + " " + component.get("caption", "") for component in components])
        return RequirementAnalyzer(self.kb)._guess_domain(joined)
