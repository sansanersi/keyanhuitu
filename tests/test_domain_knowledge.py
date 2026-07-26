import json
import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from knowledge_base.kb_core import KnowledgeBase
from orchestrator.text_analyzer import RequirementAnalyzer


class DomainKnowledgeTest(unittest.TestCase):
    def _write_vocab(self, path):
        data = {
            "domains": {
                "biology": {
                    "name": "生物",
                    "element_categories": {
                        "signaling": {
                            "name": "信号通路",
                            "elements": [
                                {
                                    "name": "EGFR",
                                    "english": "epidermal growth factor receptor",
                                    "type": "entity",
                                    "shape": "transmembrane",
                                    "color_scheme": ["#4A90D9"],
                                    "tags": ["receptor", "cell"],
                                }
                            ],
                        }
                    },
                },
                "chemistry": {
                    "name": "化学",
                    "element_categories": {
                        "reactions": {
                            "name": "反应",
                            "elements": [
                                {
                                    "name": "Catalyst",
                                    "english": "catalyst",
                                    "type": "entity",
                                    "shape": "rounded_rect",
                                    "color_scheme": ["#E67E22"],
                                    "tags": ["reaction"],
                                }
                            ],
                        }
                    },
                },
            }
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def test_focus_domain_filters_vocabulary_and_loads_corpus(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vocab_path = os.path.join(tmpdir, "domain_vocab.json")
            corpus_dir = os.path.join(tmpdir, "corpus", "biology")
            os.makedirs(corpus_dir, exist_ok=True)
            self._write_vocab(vocab_path)

            with open(os.path.join(corpus_dir, "egfr_pathway.txt"), "w", encoding="utf-8") as f:
                f.write("EGFR signaling pathway in epithelial cells.")

            kb = KnowledgeBase(vocab_path=vocab_path, focus_domain="biology", corpus_paths=[corpus_dir])

            self.assertEqual(kb.stats["focus_domain"], "biology")
            self.assertEqual(kb.stats["corpus_documents"], 1)
            self.assertEqual(kb.vocabulary.domains, ["biology"])
            self.assertEqual(kb.stats["total_terms"], 1)

            snippets = kb.get_context_snippets("EGFR signaling")
            self.assertEqual(len(snippets), 1)
            self.assertIn("egfr_pathway", snippets[0]["title"].lower())

            analyzer = RequirementAnalyzer(kb)
            analysis = analyzer.analyze("EGFR activates downstream signals")

            self.assertEqual(analysis["domain"], "biology")
            self.assertTrue(analysis["knowledge_context"])
            self.assertEqual(analysis["knowledge_context"][0]["title"].lower(), "egfr_pathway")


if __name__ == "__main__":
    unittest.main()
