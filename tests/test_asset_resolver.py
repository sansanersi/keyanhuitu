import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from knowledge_base.element_library import ElementLibrary, ElementTemplate
from orchestrator.asset_resolver import AssetResolver
from orchestrator.workflow_schema import empty_workflow


class FakeBioicons:
    available = True

    def suggest(self, text, top_k=1):
        if "EGFR" not in text and "receptor" not in text.lower():
            return []
        return [
            {
                "name": "receptor_icon",
                "category": "signaling",
                "svg_path": "icons/receptor.svg",
                "score": 3.5,
            }
        ]


class AssetResolverTest(unittest.TestCase):
    def _workflow(self):
        workflow = empty_workflow("绘制 EGFR 信号通路")
        workflow["workflow_steps"] = [{"id": "step_1", "name": "识别元素", "outputs": ["el_0"]}]
        workflow["quality_checks"] = ["元素可绘制"]
        workflow["elements"] = [
            {
                "id": "el_0",
                "name": "EGFR",
                "category": "receptor",
                "role": "primary",
                "visual_prompt": "EGFR receptor",
                "asset_hint": {
                    "shape": "transmembrane",
                    "color_scheme": ["#4A90D9"],
                    "english": "receptor",
                },
            }
        ]
        return workflow

    def test_resolver_adds_ranked_asset_matches_to_workflow_elements(self):
        library = ElementLibrary()
        library._reg(
            ElementTemplate(
                name="受体",
                english_name="receptor",
                domain="biology",
                category="signaling component",
                shape="transmembrane",
                color_scheme=["#2F6FBA"],
                tags=["egfr", "membrane"],
                description="EGFR receptor on membrane",
            )
        )

        workflow = AssetResolver(element_library=library, bioicons=FakeBioicons()).resolve_workflow(self._workflow())
        matches = workflow["elements"][0]["asset_matches"]

        self.assertEqual(matches[0]["source"], "element_library")
        self.assertEqual(matches[0]["shape"], "transmembrane")
        self.assertEqual(matches[1]["source"], "bioicons")
        self.assertEqual(matches[1]["svg_path"], "icons/receptor.svg")
        self.assertEqual(workflow["elements"][0]["selected_asset"]["source"], "element_library")

    def test_resolver_falls_back_to_workflow_asset_hint(self):
        workflow = AssetResolver().resolve_workflow(self._workflow())
        matches = workflow["elements"][0]["asset_matches"]

        self.assertEqual(matches, [
            {
                "source": "workflow_hint",
                "name": "EGFR",
                "shape": "transmembrane",
                "color_scheme": ["#4A90D9"],
                "score": 0.1,
            }
        ])
        self.assertEqual(workflow["elements"][0]["selected_asset"]["source"], "workflow_hint")


if __name__ == "__main__":
    unittest.main()
