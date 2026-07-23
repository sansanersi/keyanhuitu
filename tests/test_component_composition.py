import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from orchestrator.component_planner import ComponentPlanner
from orchestrator.pipeline import SciIllustPipeline
from drawing.component_composer import ComponentComposer


class FakeClient:
    def __init__(self, response):
        self.response = response

    def generate(self, prompt, model=None, temperature=0.1, max_tokens=2048, system=None):
        return self.response


class ComponentCompositionTest(unittest.TestCase):
    def test_planner_parses_model_json_contract(self):
        response = """
        {
          "title": "EGFR signaling",
          "layout": "hierarchical",
          "style": "science",
          "components": [
            {"id": "egf", "name": "EGF", "type": "image_text", "image_key": "protein", "caption": "配体"},
            {"id": "egfr", "name": "EGFR", "type": "image_text", "image_key": "receptor", "caption": "受体"}
          ],
          "connections": [
            {"source": "egf", "target": "egfr", "label": "结合", "type": "arrow"}
          ]
        }
        """
        plan = ComponentPlanner(llm_client=FakeClient(response)).plan("EGF binds EGFR", model="qwen3.5:4b")

        self.assertEqual(plan["layout"], "hierarchical")
        self.assertEqual(len(plan["components"]), 2)
        self.assertEqual(plan["connections"][0]["label"], "结合")

    def test_planner_falls_back_to_component_blueprint_without_json(self):
        plan = ComponentPlanner(llm_client=FakeClient("我来帮你整理资料")).plan(
            "EGF activates EGFR and then RAS",
            model="qwen3.5:4b",
        )

        self.assertGreaterEqual(len(plan["components"]), 3)
        self.assertGreaterEqual(len(plan["connections"]), 2)
        self.assertEqual(plan["source"], "fallback")

    def test_planner_maps_chinese_component_ids_in_connections(self):
        response = """
        {
          "title": "细胞结构",
          "layout": "hierarchical",
          "style": "science",
          "components": [
            {"id": "细胞核", "name": "细胞核", "type": "image_text", "image_key": "nucleus", "caption": "遗传信息"},
            {"id": "DNA", "name": "DNA", "type": "image_text", "image_key": "dna", "caption": "遗传物质"}
          ],
          "connections": [
            {"source": "细胞核", "target": "DNA", "label": "包含", "type": "arrow"}
          ]
        }
        """
        plan = ComponentPlanner(llm_client=FakeClient(response)).plan("细胞核包含 DNA", model="qwen3.5:4b")

        self.assertEqual(len(plan["connections"]), 1)
        self.assertEqual(plan["connections"][0]["target"], "DNA")

    def test_component_composer_renders_image_text_components_and_connections(self):
        plan = {
            "title": "Signal Pathway",
            "layout": "hierarchical",
            "style": "science",
            "components": [
                {"id": "egf", "name": "EGF", "type": "image_text", "image_key": "protein", "caption": "配体"},
                {"id": "egfr", "name": "EGFR", "type": "image_text", "image_key": "receptor", "caption": "受体"},
            ],
            "connections": [
                {"source": "egf", "target": "egfr", "label": "结合", "type": "arrow"}
            ],
        }

        svg = ComponentComposer().render(plan, width=900, height=600)

        self.assertIn('class="image-text-component"', svg)
        self.assertIn('class="component-visual"', svg)
        self.assertIn('class="component-title"', svg)
        self.assertIn('marker-end="url(#component-arrow)"', svg)
        self.assertIn("结合", svg)

    def test_pipeline_component_mode_returns_component_svg(self):
        result = SciIllustPipeline().process_components(
            "EGF activates EGFR and then RAS",
            model="",
            canvas_width=900,
            canvas_height=600,
        )

        self.assertEqual(result["mode"], "components")
        self.assertIn('class="image-text-component"', result["svg"])
        self.assertIn('marker-end="url(#component-arrow)"', result["svg"])
        self.assertGreaterEqual(len(result["components"]), 3)


if __name__ == "__main__":
    unittest.main()
