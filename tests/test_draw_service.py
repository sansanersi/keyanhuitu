import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from web_app.services.draw_service import DrawService


class DrawServiceTest(unittest.TestCase):
    def test_draw_returns_missing_text_error_for_empty_payload(self):
        service = DrawService(knowledge_base=None, pipeline_factory=lambda: None)

        result = service.draw({})

        self.assertEqual(result["success"], False)
        self.assertEqual(result["error"], "missing_text")

    def test_workflow_returns_missing_text_error_for_empty_payload(self):
        service = DrawService(knowledge_base=None, pipeline_factory=lambda: None)

        result = service.workflow({})

        self.assertEqual(result["success"], False)
        self.assertEqual(result["error"], "missing_text")

    def test_workflow_returns_valid_schema(self):
        class FakeAnalyzer:
            def analyze(self, text):
                return {
                    "domain": "biology",
                    "figure_type": "pathway_diagram",
                    "layout": "hierarchical",
                    "style": "science",
                    "view_type": "2d_top",
                    "elements": [
                        {"id": "el_0", "name": "EGF", "type": "protein", "shape": "rounded_rect"},
                        {"id": "el_1", "name": "EGFR", "type": "receptor", "shape": "transmembrane"},
                    ],
                    "relations": [
                        {
                            "source": "el_0",
                            "target": "el_1",
                            "type": "activates",
                            "relation_type": "activates",
                            "label": "激活",
                            "directed": True,
                        }
                    ],
                }

        service = DrawService(
            knowledge_base=object(),
            pipeline_factory=lambda: None,
            analyzer_factory=lambda: FakeAnalyzer(),
        )

        result = service.workflow({"text": "EGF activates EGFR", "canvas_width": 900, "canvas_height": 600})

        self.assertTrue(result["success"])
        self.assertEqual(result["workflow"]["schema_version"], "1.0")
        self.assertEqual(result["workflow"]["composition"]["canvas"], {"width": 900, "height": 600})
        self.assertEqual(result["errors"], [])

    def test_workflow_enriches_elements_with_asset_matches(self):
        class FakeAnalyzer:
            def analyze(self, text):
                return {
                    "domain": "biology",
                    "figure_type": "pathway_diagram",
                    "layout": "hierarchical",
                    "style": "science",
                    "view_type": "2d_top",
                    "elements": [{"id": "el_0", "name": "EGFR", "type": "receptor", "shape": "transmembrane"}],
                    "relations": [],
                }

        class FakeAssetResolver:
            def resolve_workflow(self, workflow):
                workflow["elements"][0]["asset_matches"] = [{"source": "workflow_hint", "name": "EGFR"}]
                workflow["elements"][0]["selected_asset"] = {"source": "workflow_hint", "name": "EGFR"}
                return workflow

        service = DrawService(
            knowledge_base=object(),
            pipeline_factory=lambda: None,
            analyzer_factory=lambda: FakeAnalyzer(),
            asset_resolver_factory=lambda: FakeAssetResolver(),
        )

        result = service.workflow({"text": "EGFR"})

        self.assertTrue(result["success"])
        self.assertEqual(result["workflow"]["elements"][0]["selected_asset"]["source"], "workflow_hint")

    def test_draw_uses_component_mode_response_shape(self):
        class FakePipeline:
            def process_components(self, *args, **kwargs):
                return {
                    "mode": "components",
                    "svg": "<svg></svg>",
                    "analysis": {"domain": "biology", "analysis_summary": "ok"},
                    "components": [{"id": "c1", "name": "EGFR", "image_key": "receptor", "caption": "caption"}],
                    "connections": [{"source": "c1", "target": "c2", "type": "arrow", "label": "binds"}],
                    "component_plan": {"title": "plan"},
                }

        service = DrawService(
            knowledge_base=None,
            pipeline_factory=lambda: FakePipeline(),
            timestamp_factory=lambda: "2026-07-29 11:28:00",
        )

        result = service.draw({"text": "EGFR pathway", "model": "qwen3.5:4b", "style": "science"})

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "components")
        self.assertEqual(result["elements"][0]["shape"], "receptor")
        self.assertEqual(result["relations"][0]["label"], "binds")
        self.assertEqual(result["timestamp"], "2026-07-29 11:28:00")

    def test_draw_fills_missing_style_and_figure_type_from_analyzer(self):
        class FakeAnalyzer:
            def analyze(self, text):
                return {"figure_type": "pathway_diagram", "style": "science"}

        class FakeRelation:
            source = "EGF"
            target = "EGFR"
            relation_type = "activates"
            directed = True

        class FakePipeline:
            def __init__(self):
                self.calls = []

            def process(self, text, **kwargs):
                self.calls.append((text, kwargs))
                return {
                    "mode": "elements",
                    "svg": "<svg></svg>",
                    "analysis": {"domain": "biology", "analysis_summary": "ok"},
                    "elements": [{"name": "EGFR", "shape": "receptor"}],
                    "relations": [FakeRelation()],
                    "component_plan": None,
                }

        pipeline = FakePipeline()
        service = DrawService(
            knowledge_base=object(),
            pipeline_factory=lambda: pipeline,
            analyzer_factory=lambda: FakeAnalyzer(),
            timestamp_factory=lambda: "2026-07-29 11:29:00",
        )

        result = service.draw({"text": "EGF activates EGFR", "layout": "hierarchical"})

        self.assertTrue(result["success"])
        self.assertEqual(result["analysis"]["figure_type"], "pathway_diagram")
        self.assertEqual(result["analysis"]["style"], "science")
        self.assertEqual(result["relations"][0]["type"], "activates")
        self.assertEqual(pipeline.calls[0][1]["figure_type"], "pathway_diagram")
        self.assertEqual(pipeline.calls[0][1]["style_name"], "science")


if __name__ == "__main__":
    unittest.main()
