"""Draw orchestration for the web application."""

from datetime import datetime


class DrawService:
    def __init__(
        self,
        knowledge_base,
        pipeline_factory,
        analyzer_factory=None,
        asset_resolver_factory=None,
        timestamp_factory=None,
    ):
        self.kb = knowledge_base
        self.pipeline_factory = pipeline_factory
        self.analyzer_factory = analyzer_factory
        self.asset_resolver_factory = asset_resolver_factory
        self.timestamp_factory = timestamp_factory or (lambda: datetime.now())

    def draw(self, payload):
        data = payload or {}
        text = (data.get("text", "") or "").strip()
        if not text:
            return {"success": False, "error": "missing_text"}

        figure_type = data.get("figure_type", "")
        style = data.get("style", "")
        layout = data.get("layout", "")
        model = data.get("model", "")
        canvas_width = int(data.get("canvas_width", 900))
        canvas_height = int(data.get("canvas_height", 600))

        if not figure_type or not style:
            analysis = self._analyzer().analyze(text)
            figure_type = figure_type or analysis["figure_type"]
            style = style or analysis["style"]

        result = self._render(
            text=text,
            model=model,
            figure_type=figure_type,
            style=style,
            layout=layout,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
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
                relation_list.append(
                    {
                        "source": getattr(relation, "source", ""),
                        "target": getattr(relation, "target", ""),
                        "type": getattr(relation, "relation_type", "connected_to"),
                        "directed": getattr(relation, "directed", False),
                    }
                )

        return {
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
            "timestamp": str(self.timestamp_factory()),
        }

    def workflow(self, payload):
        data = payload or {}
        text = (data.get("text", "") or "").strip()
        if not text:
            return {"success": False, "error": "missing_text"}

        canvas_width = int(data.get("canvas_width", 1000))
        canvas_height = int(data.get("canvas_height", 700))
        analysis = self._analyzer().analyze(text)

        from orchestrator.workflow_schema import validate_workflow, workflow_from_analysis

        workflow = workflow_from_analysis(
            text,
            analysis,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
        )
        workflow = self._asset_resolver().resolve_workflow(workflow)
        return {"success": True, "workflow": workflow, "errors": validate_workflow(workflow)}

    def _analyzer(self):
        if self.analyzer_factory:
            return self.analyzer_factory()
        from orchestrator.text_analyzer import RequirementAnalyzer

        return RequirementAnalyzer(self.kb)

    def _asset_resolver(self):
        if self.asset_resolver_factory:
            return self.asset_resolver_factory()
        from orchestrator.asset_resolver import AssetResolver

        return AssetResolver()

    def _render(self, text, model, figure_type, style, layout, canvas_width, canvas_height):
        pipeline = self.pipeline_factory()
        if model:
            return pipeline.process_components(
                text,
                model=model,
                style_name=style,
                layout=layout or "hierarchical",
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                auto_render=True,
            )

        from drawing.layout_engine import LayoutType

        layout_map = {
            "force_directed": LayoutType.FORCE_DIRECTED,
            "hierarchical": LayoutType.HIERARCHICAL,
            "grid": LayoutType.GRID,
            "radial": LayoutType.RADIAL,
        }
        return pipeline.process(
            text,
            figure_type=figure_type,
            style_name=style,
            layout_type=layout_map.get(layout) if layout else None,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            auto_render=True,
        )
