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
