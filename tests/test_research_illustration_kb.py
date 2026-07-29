import json
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "sci-illust-system", "web_app", "data", "structured_kb")


class ResearchIllustrationKbTest(unittest.TestCase):
    def _load_json(self, name):
        path = os.path.join(DATA_DIR, name)
        self.assertTrue(os.path.exists(path), f"missing file: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_structured_kb_files_exist_and_have_expected_shape(self):
        terms = self._load_json("research_illustration_terms.json")
        relations = self._load_json("research_illustration_relations.json")
        mappings = self._load_json("research_illustration_asset_mapping.json")
        layouts = self._load_json("research_illustration_layout_rules.json")

        self.assertEqual(terms["domain"], "research_illustration")
        self.assertGreaterEqual(len(terms["terms"]), 10)
        self.assertIn("受体", [item["name"] for item in terms["terms"]])

        self.assertEqual(relations["domain"], "research_illustration")
        self.assertGreaterEqual(len(relations["relations"]), 5)
        self.assertIn("activates", [item["relation_type"] for item in relations["relations"]])

        self.assertEqual(mappings["domain"], "research_illustration")
        self.assertGreaterEqual(len(mappings["asset_mappings"]), 5)
        self.assertIn("receptor", [item["normalized_term"] for item in mappings["asset_mappings"]])

        self.assertEqual(layouts["domain"], "research_illustration")
        self.assertGreaterEqual(len(layouts["layout_rules"]), 4)
        self.assertIn("pathway_diagram", [item["figure_type"] for item in layouts["layout_rules"]])


if __name__ == "__main__":
    unittest.main()
