import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from drawing.layout_engine import LayoutType
from orchestrator.pipeline import SciIllustPipeline
from orchestrator.text_analyzer import RequirementAnalyzer


class CorePipelineTest(unittest.TestCase):
    def test_analyzer_returns_stable_json_shape(self):
        analysis = RequirementAnalyzer().analyze("EGF activates EGFR and then RAS")

        self.assertEqual(
            set(["domain", "figure_type", "elements", "relations", "layout", "style"]).issubset(analysis.keys()),
            True,
        )
        self.assertIsInstance(analysis["elements"], list)
        self.assertIsInstance(analysis["relations"], list)
        self.assertIsInstance(analysis["layout"], str)
        self.assertIsInstance(analysis["style"], str)

    def test_pipeline_renders_elements_arrows_labels_and_layout(self):
        result = SciIllustPipeline().process(
            "EGF activates EGFR and then RAS",
            layout_type=LayoutType.HIERARCHICAL,
            canvas_width=900,
            canvas_height=600,
            auto_render=True,
        )

        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(len(result["elements"]), 3)
        self.assertGreaterEqual(len(result["relations"]), 2)
        self.assertIn('marker-end="url(#arrowhead)"', result["svg"])
        self.assertIn('class="element-label"', result["svg"])
        self.assertIn('transform="translate(', result["svg"])
        self.assertEqual(result["analysis"]["layout"], "hierarchical")


if __name__ == "__main__":
    unittest.main()
