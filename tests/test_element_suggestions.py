import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from knowledge_base.element_library import ElementLibrary, ElementTemplate


class ElementSuggestionTest(unittest.TestCase):
    def test_suggest_matches_tokenized_english_phrase(self):
        library = ElementLibrary()
        library._reg(
            ElementTemplate(
                name="受体",
                english_name="receptor",
                domain="biology",
                category="signaling component",
                shape="transmembrane",
                tags=["signal", "membrane"],
                description="signal receptor on membrane",
            )
        )
        library._reg(
            ElementTemplate(
                name="激酶",
                english_name="kinase",
                domain="biology",
                category="signaling component",
                shape="rounded_rect",
                tags=["signal", "phosphorylation"],
                description="downstream signaling kinase",
            )
        )

        results = library.suggest("EGFR signaling", top_k=5)

        self.assertGreaterEqual(len(results), 2)
        english_names = [item.english_name for item in results]
        self.assertIn("receptor", english_names)
        self.assertIn("kinase", english_names)


if __name__ == "__main__":
    unittest.main()
