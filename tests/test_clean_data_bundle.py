import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.clean_data_bundle import (
    clean_element_literature_map,
    clean_element_record,
    clean_elements,
    clean_entity_record,
    clean_literature_record,
    clean_relation_record,
    is_probable_noise_text,
    normalize_doi,
    normalize_url,
    prepare_output_dirs,
    run_cleaning,
    sanitize_filename,
    strip_html_to_text,
)


class CleanDataBundleScaffoldTest(unittest.TestCase):
    def test_prepare_output_dirs_creates_cleaned_and_report_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = prepare_output_dirs(Path(tmpdir), overwrite=False)

            self.assertTrue(paths["cleaned_root"].exists())
            self.assertTrue(paths["reports_root"].exists())
            self.assertTrue((paths["cleaned_root"] / "elements").exists())
            self.assertTrue((paths["cleaned_root"] / "literature").exists())
            self.assertTrue((paths["cleaned_root"] / "literature" / "texts").exists())
            self.assertTrue((paths["cleaned_root"] / "mappings").exists())
            self.assertTrue((paths["cleaned_root"] / "kg").exists())


class CleanDataBundleUtilityTest(unittest.TestCase):
    def test_strip_html_to_text_removes_tags_and_compacts_whitespace(self):
        text = strip_html_to_text("<h4>Aims</h4> Test<br>value")
        self.assertEqual(text, "Aims Test value")

    def test_normalize_doi_accepts_doi_url(self):
        self.assertEqual(
            normalize_doi(" https://doi.org/10.1016/J.CELL.2005.02.001 "),
            "10.1016/j.cell.2005.02.001",
        )

    def test_normalize_url_rejects_non_http_protocol(self):
        self.assertEqual(normalize_url("ftp://example.com/a"), "")

    def test_is_probable_noise_text_flags_html_tag_name(self):
        self.assertTrue(is_probable_noise_text("h4"))

    def test_sanitize_filename_truncates_long_windows_unsafe_name(self):
        value = "Establishment of Cell Cultures from the Cavefish &lt;italic&gt;Astyanax mexicanus&lt;/italic&gt;: A Resource for in vitro Studies of Supernumerary B Chromosome Biology"
        cleaned = sanitize_filename(value, "fallback")
        self.assertLessEqual(len(cleaned), 120)
        self.assertNotIn(":", cleaned)


class CleanElementsTest(unittest.TestCase):
    def test_clean_elements_merges_duplicate_ids_and_sorts_tags(self):
        domain_vocab = {"domains": {}}
        kb_elements = [
            {
                "element_id": "mitochondrion",
                "name": "线粒体",
                "english": "mitochondrion",
                "domain": "生物学",
                "category": "细胞器",
                "shape": "bean",
                "tags": ["ATP", "能量", "ATP"],
            },
            {
                "element_id": "mitochondrion",
                "name": "线粒体",
                "english": "mitochondrion",
                "domain": "生物学",
                "category": "细胞器",
                "shape": "bean",
                "tags": ["动力"],
            },
        ]

        cleaned = clean_elements(domain_vocab, kb_elements, [])

        item = cleaned["element_index"]["mitochondrion"]
        self.assertEqual(item["tags"], ["ATP", "动力", "能量"])
        self.assertEqual(item["source_count"], 2)

    def test_clean_element_record_returns_none_when_name_and_english_missing(self):
        self.assertIsNone(clean_element_record({"element_id": ""}, "kb.json", []))

    def test_clean_element_record_normalizes_domain_and_category_to_bilingual_standard_names(self):
        cleaned = clean_element_record(
            {
                "element_id": "mitochondrion",
                "name": "线粒体",
                "english": "mitochondrion",
                "domain": "����ѧ",
                "category": "ϸ����",
                "shape": "bean",
                "tags": ["ATP"],
            },
            "kb.json",
            [],
        )

        self.assertEqual(cleaned["domain"], "生物学")
        self.assertEqual(cleaned["domain_en"], "biology")
        self.assertEqual(cleaned["category"], "细胞器")
        self.assertEqual(cleaned["category_en"], "organelles")


class CleanLiteratureTest(unittest.TestCase):
    def test_clean_literature_record_strips_html_and_normalizes_doi(self):
        row = {
            "id": "1",
            "title": " Example ",
            "content": "<h4>Aims</h4>Body",
            "doi": "https://doi.org/10.1000/ABC",
            "url": "https://example.org/paper",
        }

        cleaned = clean_literature_record(row, "normalized/1.json", "1", [])

        self.assertEqual(cleaned["content"], "Aims Body")
        self.assertEqual(cleaned["doi"], "10.1000/abc")

    def test_clean_literature_record_returns_none_when_cleaned_content_empty(self):
        self.assertIsNone(
            clean_literature_record({"id": "x", "title": "A", "content": "<div> </div>"}, "f.json", "x", [])
        )


class CleanMappingTest(unittest.TestCase):
    def test_clean_element_literature_map_keeps_only_known_elements_and_docs(self):
        raw_map = {"linkage": {"mitochondrion": ["10.1000/abc", "bad-ref"], "ghost": ["10.1000/abc"]}}
        element_index = {"mitochondrion": {"element_id": "mitochondrion"}}
        literature_index = {"10.1000/abc": {"record_id": "doc-1"}}
        exceptions = []

        cleaned = clean_element_literature_map(raw_map, element_index, literature_index, exceptions)

        self.assertEqual(cleaned["linkage"]["mitochondrion"], ["10.1000/abc"])
        self.assertNotIn("ghost", cleaned["linkage"])
        self.assertGreaterEqual(len(exceptions), 1)


class CleanKgTest(unittest.TestCase):
    def test_clean_entity_record_filters_noise_entity(self):
        self.assertIsNone(clean_entity_record({"name": "h4", "aliases": []}, []))

    def test_clean_relation_record_filters_low_confidence_and_broken_subject(self):
        self.assertIsNone(
            clean_relation_record(
                {"subject": "", "relation": "activates", "object": "AKT", "confidence": 0.2},
                0.8,
                [],
            )
        )


class CleanDataBundleIntegrationTest(unittest.TestCase):
    def test_run_cleaning_writes_outputs_and_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_root = Path(tmpdir)
            sample_zip_path = temp_root / "sample.zip"
            output_root = temp_root / "output"
            self._create_sample_zip(sample_zip_path)

            result = run_cleaning(
                sample_zip_path,
                output_root,
                min_relation_confidence=0.8,
                overwrite=True,
                sample_limit=5,
            )

            self.assertTrue((output_root / "data_2_cleaned" / "elements" / "element_index.cleaned.json").exists())
            self.assertTrue((output_root / "data_2_reports" / "cleaning_summary.json").exists())
            self.assertTrue((output_root / "data_2_reports" / "validation_summary.json").exists())
            self.assertTrue((output_root / "data_2_reports" / "exceptions.jsonl").exists())
            self.assertIn("validation", result)
            self.assertIn("passed", result["validation"])

    def _create_sample_zip(self, path: Path):
        domain_vocab = {
            "metadata": {"version": "1.0"},
            "domains": {
                "biology": {
                    "name": "生物学",
                    "description": "desc",
                    "element_categories": {
                        "organelle": {
                            "name": "细胞器",
                            "elements": [
                                {
                                    "name": "线粒体",
                                    "english": "mitochondrion",
                                    "shape": "bean",
                                    "tags": ["ATP", "能量"],
                                    "color_scheme": ["#E74C3C"],
                                    "type": "organelle",
                                }
                            ],
                        }
                    },
                }
            },
            "figure_types": [],
            "view_types": [],
            "spatial_relations": [],
            "style_references": [],
        }
        kb_a_elements = [
            {
                "element_id": "mitochondrion",
                "name": "线粒体",
                "english": "mitochondrion",
                "domain": "生物学",
                "category": "细胞器",
                "shape": "bean",
                "color_scheme": ["#E74C3C"],
                "tags": ["ATP", "能量"],
                "svg_file_path": "",
                "description": "desc",
            }
        ]
        element_map = {
            "generated_at": "2026-07-28T13:47:41",
            "description": "map",
            "element_count": 1,
            "literature_count": 1,
            "linked_elements": 1,
            "total_links": 2,
            "linkage": {"mitochondrion": ["10.1000/abc", "bad-ref"]},
        }
        normalized_doc = {
            "id": "doc-1",
            "source": "europe_pmc",
            "title": " Mito paper ",
            "content": "<h4>Aims</h4>Mito body",
            "keywords": ["Mito"],
            "authors": ["Alice"],
            "url": "https://example.org/doc-1",
            "year": 2025,
            "type": "article",
            "fetched_at": "2026-07-28T00:00:00",
        }
        literature_row = {
            "title": "Mito paper",
            "abstract": "Mito body",
            "conclusion": "done",
            "doi": "10.1000/abc",
            "url": "https://example.org/doc-1",
            "authors": ["Alice"],
            "journal": "Cell",
            "keywords": ["Mito"],
            "matched_terms": ["mitochondrion"],
            "domain": "biology",
            "year": 2025,
        }
        entities = {
            "metadata": {"total": 2},
            "entities": [
                {"id": 1, "name": "线粒体", "type": "organelle", "aliases": ["mitochondria"], "frequency": 2, "confidence": 0.9},
                {"id": 2, "name": "h4", "type": "protein", "aliases": [], "frequency": 1, "confidence": 0.6},
            ],
        }
        relations = [
            {"subject": "线粒体", "relation": "activates", "object": "ATP合成", "confidence": 0.9, "source_doc": "doc-1"},
            {"subject": "", "relation": "activates", "object": "AKT", "confidence": 0.2, "source_doc": "doc-2"},
        ]
        triples = {
            "metadata": {"total": 2},
            "triples": [
                {"id": 1, "subject": "线粒体", "relation": "activates", "object": "ATP合成", "confidence": 0.9, "sources": ["doc-1"], "created_at": "2026-07-28T00:00:00"},
                {"id": 2, "subject": "h4", "relation": "unknown_relation", "object": "ATP合成", "confidence": 0.9, "sources": ["doc-1"], "created_at": "2026-07-28T00:00:00"},
            ],
        }

        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("data_2/data/domain_vocab.json", json.dumps(domain_vocab, ensure_ascii=False))
            zf.writestr("data_2/data/kb_exports/kb_a_elements.json", json.dumps(kb_a_elements, ensure_ascii=False))
            zf.writestr("data_2/data/kb_exports/element_literature_map.json", json.dumps(element_map, ensure_ascii=False))
            zf.writestr("data_2/data/kb_exports/kb_b_literature.jsonl", json.dumps(literature_row, ensure_ascii=False) + "\n")
            zf.writestr("data_2/data/normalized/doc-1.json", json.dumps(normalized_doc, ensure_ascii=False))
            zf.writestr("data_2/data/kg_output/entities.json", json.dumps(entities, ensure_ascii=False))
            zf.writestr("data_2/data/kg_output/relations.json", json.dumps(relations, ensure_ascii=False))
            zf.writestr("data_2/data/kg_output/triples.json", json.dumps(triples, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
