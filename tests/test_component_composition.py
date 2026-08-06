import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from orchestrator.component_planner import ComponentPlanner
from orchestrator.pipeline import SciIllustPipeline
from knowledge_base.bioicons_library import BioiconsLibrary
from drawing.component_composer import ComponentComposer
from drawing.layout_engine import LayoutEdge, LayoutEngine, LayoutNode, LayoutType


class FakeClient:
    def __init__(self, response):
        self.response = response

    def generate(self, prompt, model=None, temperature=0.1, max_tokens=2048, system=None):
        return self.response


class ComponentCompositionTest(unittest.TestCase):
    def _build_bioicon_fixture(self, root_dir):
        icons_dir = os.path.join(root_dir, "static", "icons")
        target_dir = os.path.join(icons_dir, "cc-by-4.0", "Cell_culture", "DBCLS")
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(icons_dir, "icons.json"), "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "name": "2-cell_embryo",
                        "category": "Cell_culture",
                        "license": "cc-by-4.0",
                        "author": "DBCLS",
                    }
                ],
                f,
            )
        with open(os.path.join(target_dir, "2-cell_embryo.svg"), "w", encoding="utf-8") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 72"><circle cx="36" cy="36" r="28"/></svg>')

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

        self.assertIn('class="figure-background"', svg)
        self.assertIn('id="soft-shadow"', svg)
        self.assertIn('class="image-text-component"', svg)
        self.assertIn('class="component-shell"', svg)
        self.assertIn('class="component-visual"', svg)
        self.assertIn('class="component-title"', svg)
        self.assertIn('marker-end="url(#component-arrow)"', svg)
        self.assertIn("结合", svg)

    def test_component_composer_embeds_bioicon_svg_assets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._build_bioicon_fixture(tmpdir)
            planner = ComponentPlanner(bioicons=BioiconsLibrary(tmpdir), llm_client=FakeClient(
                """
                {
                  "title": "Embryo",
                  "layout": "hierarchical",
                  "style": "science",
                  "components": [
                    {"id": "embryo", "name": "2-cell_embryo", "type": "image_text", "image_key": "process", "caption": "早期胚胎"}
                  ],
                  "connections": []
                }
                """
            ))

            plan = planner.plan("2-cell embryo", model="qwen3.5:4b")
            svg = ComponentComposer().render(plan, width=900, height=600)

            self.assertIn('class="bioicon-art"', svg)
            self.assertIn("data:image/svg+xml;base64", svg)
            self.assertEqual(plan["components"][0]["asset_source"], "bioicons")
            self.assertTrue(plan["components"][0]["svg_path"].endswith("2-cell_embryo.svg"))

    def test_component_composer_hides_redundant_caption_text(self):
        plan = {
            "title": "Signal Pathway",
            "layout": "hierarchical",
            "style": "science",
            "components": [
                {
                    "id": "egf_egfr",
                    "name": "EGF配体结合EGFR受体",
                    "type": "image_text",
                    "image_key": "receptor",
                    "caption": "EGF与EGFR的相互作用",
                }
            ],
            "connections": [],
        }

        svg = ComponentComposer().render(plan, width=900, height=600)

        self.assertIn("EGF配体结合EGFR受体", svg)
        self.assertNotIn("EGF与EGFR的相互作用", svg)

    def test_component_composer_hides_redundant_english_caption_text(self):
        plan = {
            "title": "Signal Pathway",
            "layout": "hierarchical",
            "style": "science",
            "components": [
                {
                    "id": "egf_binding",
                    "name": "EGF Receptor Binding",
                    "type": "image_text",
                    "image_key": "receptor",
                    "caption": "EGF binding to EGFR",
                }
            ],
            "connections": [],
        }

        svg = ComponentComposer().render(plan, width=900, height=600)

        self.assertIn("EGF Receptor Bi…", svg)
        self.assertNotIn("EGF binding to EGFR", svg)

    def test_component_composer_hides_caption_by_default(self):
        plan = {
            "title": "Signal Pathway",
            "layout": "hierarchical",
            "style": "science",
            "components": [
                {
                    "id": "nucleus_step",
                    "name": "信号传递至细胞核",
                    "type": "image_text",
                    "image_key": "nucleus",
                    "caption": "基因表达启动",
                }
            ],
            "connections": [],
        }

        svg = ComponentComposer().render(plan, width=900, height=600)

        self.assertIn("信号传递至细胞核", svg)
        self.assertNotIn("基因表达启动", svg)

    def test_component_composer_wraps_dense_hierarchical_components(self):
        plan = {
            "title": "Dense pathway",
            "layout": "hierarchical",
            "components": [
                {"id": "c" + str(index), "name": "C" + str(index), "caption": "step"}
                for index in range(8)
            ],
            "connections": [
                {"source": "c" + str(index), "target": "c" + str(index + 1), "label": "next"}
                for index in range(7)
            ],
        }

        components = ComponentComposer()._layout_components(plan, 900, 600)
        ys = sorted(set(round(component["y"]) for component in components))
        first_row = [component for component in components if round(component["y"]) == ys[0]]

        self.assertGreaterEqual(len(ys), 2)
        self.assertEqual(len(first_row), 4)
        self.assertGreater(min(component["x"] for component in components), 40)

    def test_hierarchical_layout_spreads_chain_left_to_right(self):
        nodes = [LayoutNode("n" + str(index), "N" + str(index), 84, 58) for index in range(8)]
        edges = [
            LayoutEdge("n" + str(index), "n" + str(index + 1), directed=True)
            for index in range(7)
        ]

        result = LayoutEngine().layout(nodes, edges, LayoutType.HIERARCHICAL, 900, 600)
        xs = [result.positions["n" + str(index)][0] for index in range(8)]

        self.assertGreater(max(xs) - min(xs), 650)
        self.assertEqual(xs, sorted(xs))

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
