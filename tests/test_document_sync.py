import os
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

from web_app.database import KnowledgeDatabase
from web_app.document_processor import DocumentProcessor
from text_kb.graphrag_manager import GraphRAGTextKBManager


class DocumentSyncTest(unittest.TestCase):
    def test_sync_uploads_registers_existing_files_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = os.path.join(tmpdir, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            db_path = os.path.join(tmpdir, "knowledge.db")

            file_path = os.path.join(upload_dir, "pathway_notes.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("EGFR signaling pathway and receptor activation.")

            text_kb_dir = os.path.join(tmpdir, "text_kb")
            text_kb_manager = GraphRAGTextKBManager(base_dir=text_kb_dir, focus_domain="biology")
            processor = DocumentProcessor(upload_dir=upload_dir, focus_domain="biology", text_kb_manager=text_kb_manager)
            processor.db = KnowledgeDatabase(db_path)

            result = processor.sync_uploads()
            documents = processor.db.list_documents()
            text_kb_status = text_kb_manager.status("biology")

            self.assertEqual(result["synced"], 1)
            self.assertEqual(result["removed"], 0)
            self.assertEqual(len(documents), 1)
            self.assertEqual(documents[0]["filename"], "pathway_notes.md")
            self.assertEqual(documents[0]["vectorized"], 1)
            self.assertEqual(text_kb_status["raw_documents"], 1)
            self.assertEqual(text_kb_status["cleaned_documents"], 1)
            self.assertEqual(text_kb_status["input_documents"], 1)

            result_again = processor.sync_uploads()
            documents_again = processor.db.list_documents()

            self.assertEqual(result_again["synced"], 0)
            self.assertEqual(len(documents_again), 1)

    def test_sync_uploads_moves_new_text_into_incoming_queue_before_import(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = os.path.join(tmpdir, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            db_path = os.path.join(tmpdir, "knowledge.db")

            file_path = os.path.join(upload_dir, "biology_note.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("Ligand binds receptor and activates downstream pathway.")

            text_kb_dir = os.path.join(tmpdir, "text_kb")
            text_kb_manager = GraphRAGTextKBManager(base_dir=text_kb_dir, focus_domain="biology")
            processor = DocumentProcessor(upload_dir=upload_dir, focus_domain="biology", text_kb_manager=text_kb_manager)
            processor.db = KnowledgeDatabase(db_path)

            result = processor.sync_uploads()
            paths = text_kb_manager.workspace_paths("biology")

            self.assertEqual(result["synced"], 1)
            self.assertTrue(os.path.exists(os.path.join(paths["incoming_root"], "biology_note.md")))
            self.assertTrue(os.path.exists(os.path.join(paths["cleaned_root"], "biology_note.md")))


if __name__ == "__main__":
    unittest.main()
