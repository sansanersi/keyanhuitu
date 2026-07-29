import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from text_kb.graphrag_manager import GraphRAGTextKBManager


class GraphRAGWorkspaceTest(unittest.TestCase):
    def test_workspace_bootstrap_creates_expected_directories_and_templates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GraphRAGTextKBManager(base_dir=tmpdir, focus_domain="biology")

            result = manager.ensure_workspace("biology")

            self.assertTrue(os.path.isdir(result["incoming_root"]))
            self.assertTrue(os.path.isdir(os.path.join(result["incoming_root"], "pathways")))
            self.assertTrue(os.path.isdir(os.path.join(result["incoming_root"], "receptors")))
            self.assertTrue(os.path.isdir(os.path.join(result["incoming_root"], "gene_regulation")))
            self.assertTrue(os.path.isdir(os.path.join(result["incoming_root"], "figure_captions")))
            self.assertTrue(os.path.isdir(result["raw_root"]))
            self.assertTrue(os.path.isdir(result["cleaned_root"]))
            self.assertTrue(os.path.isdir(result["input_root"]))
            self.assertTrue(os.path.isfile(result["settings_yaml"]))
            self.assertTrue(os.path.isfile(result["env_file"]))
            self.assertTrue(os.path.isfile(result["manifest_file"]))
            self.assertFalse(result["initialized"])

    def test_stage_document_copies_file_to_raw_cleaned_and_graphrag_input(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GraphRAGTextKBManager(base_dir=os.path.join(tmpdir, "text_kb"), focus_domain="biology")
            source = os.path.join(tmpdir, "egfr_notes.md")
            with open(source, "w", encoding="utf-8") as f:
                f.write("# EGFR\n\nEGFR activates RAS and MAPK.\n")

            result = manager.stage_document(source, domain="biology")

            self.assertTrue(result["success"])
            self.assertTrue(os.path.exists(result["raw_path"]))
            self.assertTrue(os.path.exists(result["cleaned_path"]))
            self.assertTrue(os.path.exists(result["input_path"]))
            self.assertEqual(manager.status("biology")["raw_documents"], 1)
            self.assertEqual(manager.status("biology")["cleaned_documents"], 1)
            self.assertEqual(manager.status("biology")["input_documents"], 1)

    def test_cli_available_finds_user_level_graphrag_script(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GraphRAGTextKBManager(base_dir=tmpdir, focus_domain="biology")
            fake_exe = os.path.join(tmpdir, "Scripts", "graphrag.exe")
            os.makedirs(os.path.dirname(fake_exe), exist_ok=True)
            with open(fake_exe, "w", encoding="utf-8") as f:
                f.write("")

            with patch("text_kb.graphrag_manager.shutil.which", return_value=None), patch(
                "text_kb.graphrag_manager.sys.executable", os.path.join(tmpdir, "python.exe"), create=True
            ):
                self.assertEqual(manager._graphrag_executable(), fake_exe)
                self.assertTrue(manager.cli_available())

    def test_extract_query_answer_removes_cli_logs(self):
        manager = GraphRAGTextKBManager(base_dir=".", focus_domain="biology")
        stdout = (
            "INFO: Vector Store Args: {...}\n"
            "creating llm client with {...}\n"
            "SUCCESS: Local Search Response:\n"
            "这是最终答案。\n"
        )

        self.assertEqual(manager._extract_query_answer(stdout), "这是最终答案。")

    def test_import_documents_builds_manifest_and_skips_duplicate_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GraphRAGTextKBManager(base_dir=os.path.join(tmpdir, "text_kb"), focus_domain="biology")
            paths = manager.ensure_workspace("biology")

            source_a = os.path.join(paths["incoming_root"], "egfr_pathway.md")
            with open(source_a, "w", encoding="utf-8") as f:
                f.write("# EGFR\n\nEGFR activates RAS.\n\n")

            result = manager.import_documents(domain="biology")
            self.assertEqual(result["imported"], 1)
            self.assertEqual(result["skipped_duplicates"], 0)

            source_b = os.path.join(paths["incoming_root"], "egfr_pathway_copy.md")
            with open(source_b, "w", encoding="utf-8") as f:
                f.write("# EGFR\n\nEGFR activates RAS.\n\n")

            result_duplicate = manager.import_documents(domain="biology")
            self.assertEqual(result_duplicate["imported"], 0)
            self.assertEqual(result_duplicate["skipped_duplicates"], 1)

            with open(paths["manifest_file"], "r", encoding="utf-8") as f:
                manifest = json.load(f)

            self.assertEqual(len(manifest["documents"]), 1)
            self.assertEqual(manifest["documents"][0]["status"], "active")
            self.assertTrue(os.path.exists(manifest["documents"][0]["cleaned_path"]))

    def test_reset_workspace_clears_active_files_but_keeps_archive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GraphRAGTextKBManager(base_dir=os.path.join(tmpdir, "text_kb"), focus_domain="biology")
            paths = manager.ensure_workspace("biology")
            source = os.path.join(tmpdir, "legacy.md")
            with open(source, "w", encoding="utf-8") as f:
                f.write("legacy text")
            manager.stage_document(source, domain="biology")

            archived = os.path.join(paths["archive_root"], "legacy.md")
            with open(archived, "w", encoding="utf-8") as f:
                f.write("archived")

            manager.reset_workspace("biology")
            status = manager.status("biology")

            self.assertEqual(status["raw_documents"], 0)
            self.assertEqual(status["cleaned_documents"], 0)
            self.assertEqual(status["input_documents"], 0)
            self.assertTrue(os.path.exists(archived))

    def test_import_documents_skips_readme_and_preserves_incoming_subdir_without_flat_copy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = GraphRAGTextKBManager(base_dir=os.path.join(tmpdir, "text_kb"), focus_domain="biology")
            paths = manager.ensure_workspace("biology")
            nested = os.path.join(paths["incoming_root"], "pathways", "egfr.md")
            with open(nested, "w", encoding="utf-8") as f:
                f.write("EGFR activates RAS.")
            with open(os.path.join(paths["incoming_root"], "README.md"), "w", encoding="utf-8") as f:
                f.write("helper")

            result = manager.import_documents(domain="biology")

            self.assertEqual(result["imported"], 1)
            self.assertFalse(os.path.exists(os.path.join(paths["incoming_root"], "egfr.md")))


if __name__ == "__main__":
    unittest.main()
