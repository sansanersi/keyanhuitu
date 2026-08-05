import os
import sys
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from orchestrator.text_analyzer import RequirementAnalyzer
from orchestrator.workflow_schema import (
    DRAWING_WORKFLOW_SCHEMA,
    empty_workflow,
    normalize_workflow,
    validate_workflow,
    workflow_from_analysis,
)


class DrawingWorkflowSchemaTest(unittest.TestCase):
    def test_empty_workflow_exposes_stable_contract(self):
        workflow = empty_workflow("绘制 EGFR 信号通路")

        self.assertEqual(workflow["schema_version"], DRAWING_WORKFLOW_SCHEMA["schema_version"])
        self.assertEqual(workflow["task"]["user_requirement"], "绘制 EGFR 信号通路")
        self.assertIn("composition", workflow)
        self.assertIn("quality_checks", workflow)

    def test_workflow_from_analysis_is_valid(self):
        analysis = RequirementAnalyzer().analyze("EGF activates EGFR and then RAS")
        workflow = workflow_from_analysis("EGF activates EGFR and then RAS", analysis)

        self.assertEqual(validate_workflow(workflow), [])
        self.assertGreaterEqual(len(workflow["elements"]), 3)
        self.assertGreaterEqual(len(workflow["relations"]), 2)
        self.assertEqual(workflow["composition"]["layout"], "hierarchical")
        self.assertIn("normalized_goal", workflow["task"])

    def test_validate_workflow_reports_missing_relation_target(self):
        workflow = empty_workflow("绘制机制图")
        workflow["workflow_steps"] = [{"id": "step_1", "name": "识别元素", "outputs": ["el_0"]}]
        workflow["elements"] = [
            {
                "id": "el_0",
                "name": "EGFR",
                "category": "entity",
                "role": "primary",
                "visual_prompt": "EGFR receptor",
            }
        ]
        workflow["relations"] = [{"source": "el_0", "target": "missing", "type": "activates", "label": "激活"}]
        workflow["quality_checks"] = ["元素完整"]

        errors = validate_workflow(workflow)

        self.assertIn("relation target not found: missing", errors)

    def test_normalize_workflow_keeps_supported_defaults(self):
        workflow = normalize_workflow({"domain": "unknown", "figure_type": "bad", "composition": {"layout": "bad"}})

        self.assertEqual(workflow["domain"], "general")
        self.assertEqual(workflow["figure_type"], "schematic_diagram")
        self.assertEqual(workflow["composition"]["layout"], "hierarchical")


if __name__ == "__main__":
    unittest.main()
