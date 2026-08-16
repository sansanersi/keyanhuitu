import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.import_cleaned_bundle import (
    import_image_kb,
    import_text_kb,
    load_cleaned_bundle,
    run_import,
)


class ImportCleanedBundleTest(unittest.TestCase):
    def test_import_text_kb_only_writes_documents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cleaned_root = self._create_cleaned_bundle(root)
            db_path = root / "knowledge.db"

            result = run_import(cleaned_root, target="text_kb", db_path=db_path)

            self.assertEqual(result["text_kb"]["documents_imported"], 2)
            self.assertEqual(result["image_kb"]["entries_imported"], 0)
            self.assertEqual(result["repository_stats"]["documents"], 2)
            self.assertEqual(result["repository_stats"]["entries"], 0)

    def test_import_image_kb_only_writes_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cleaned_root = self._create_cleaned_bundle(root)
            db_path = root / "knowledge.db"

            result = run_import(cleaned_root, target="image_kb", db_path=db_path)

            self.assertEqual(result["image_kb"]["entries_imported"], 2)
            self.assertEqual(result["text_kb"]["documents_imported"], 0)
            self.assertEqual(result["repository_stats"]["entries"], 2)
            self.assertEqual(result["repository_stats"]["documents"], 0)
            self.assertEqual(result["image_kb"]["domain_counts"][0]["domain_zh"], "生物学")
            self.assertEqual(result["image_kb"]["domain_counts"][0]["domain_en"], "biology")
            self.assertEqual(result["image_kb"]["category_counts"][0]["category_zh"], "细胞器")
            self.assertEqual(result["image_kb"]["category_counts"][0]["category_en"], "organelles")

    def test_import_both_is_idempotent_for_same_cleaned_bundle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cleaned_root = self._create_cleaned_bundle(root)
            db_path = root / "knowledge.db"

            first = run_import(cleaned_root, target="both", db_path=db_path)
            second = run_import(cleaned_root, target="both", db_path=db_path)

            self.assertEqual(first["image_kb"]["entries_imported"], 2)
            self.assertEqual(first["text_kb"]["documents_imported"], 2)
            self.assertEqual(second["image_kb"]["entries_imported"], 0)
            self.assertEqual(second["text_kb"]["documents_imported"], 0)
            self.assertEqual(second["repository_stats"]["entries"], 2)
            self.assertEqual(second["repository_stats"]["documents"], 2)

    def test_load_cleaned_bundle_reads_expected_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            cleaned_root = self._create_cleaned_bundle(root)

            payload = load_cleaned_bundle(cleaned_root)

            self.assertEqual(len(payload["image_kb"]["elements"]), 2)
            self.assertEqual(len(payload["text_kb"]["documents"]), 2)

    def _create_cleaned_bundle(self, root: Path) -> Path:
        cleaned_root = root / "data_2_cleaned"
        (cleaned_root / "elements").mkdir(parents=True, exist_ok=True)
        (cleaned_root / "literature").mkdir(parents=True, exist_ok=True)

        elements = [
            {
                "element_id": "mitochondrion",
                "name": "线粒体",
                "english": "mitochondrion",
                "domain": "生物学",
                "category": "细胞器",
                "shape": "bean",
                "color_scheme": ["#E74C3C"],
                "tags": ["ATP", "能量"],
                "description": "desc",
            },
            {
                "element_id": "nucleus",
                "name": "细胞核",
                "english": "nucleus",
                "domain": "生物学",
                "category": "细胞器",
                "shape": "circle",
                "color_scheme": ["#8E44AD"],
                "tags": ["DNA"],
                "description": "desc",
            },
        ]
        documents = [
            {
                "record_id": "doc-1",
                "title": "Paper A",
                "content": "Body A",
                "doi": "10.1000/abc",
                "url": "https://example.org/a",
                "year": 2025,
                "authors": ["Alice"],
                "keywords": ["mito"],
                "journal": "Cell",
            },
            {
                "record_id": "doc-2",
                "title": "Paper B",
                "content": "Body B",
                "doi": "",
                "url": "https://example.org/b",
                "year": 2024,
                "authors": ["Bob"],
                "keywords": ["nucleus"],
                "journal": "Nature",
            },
        ]

        (cleaned_root / "elements" / "kb_a_elements.cleaned.json").write_text(
            json.dumps(elements, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (cleaned_root / "elements" / "element_index.cleaned.json").write_text(
            json.dumps({item["element_id"]: item for item in elements}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (cleaned_root / "literature" / "normalized.cleaned.jsonl").write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in documents) + "\n",
            encoding="utf-8",
        )
        return cleaned_root


if __name__ == "__main__":
    unittest.main()
