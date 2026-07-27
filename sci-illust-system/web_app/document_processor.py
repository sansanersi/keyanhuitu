import os
import re

try:
    from .database import KnowledgeDatabase
except ImportError:
    from database import KnowledgeDatabase
from text_kb.graphrag_manager import GraphRAGTextKBManager


class DocumentProcessor:
    SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json"}

    def __init__(self, upload_dir=None, focus_domain=None, text_kb_manager=None):
        self.upload_dir = upload_dir or os.path.join(os.path.dirname(__file__), "data", "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)
        self.db = KnowledgeDatabase()
        self.focus_domain = focus_domain or os.environ.get("SCI_FOCUS_DOMAIN", "biology")
        self.text_kb_manager = text_kb_manager or GraphRAGTextKBManager(focus_domain=self.focus_domain)

    def process_file(self, filepath, filename=None):
        filepath = os.path.abspath(filepath)
        filename = filename or os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.SUPPORTED_TEXT_EXTENSIONS:
            return {"success": False, "error": "unsupported file type", "filename": filename}

        content = self._extract_text(filepath, ext)
        if not content or content in ("[error]", "[unsupported]"):
            return {"success": False, "error": "no content", "filename": filename}

        doc_id = self.db.save_document(filename, filepath, ext, content, 1)
        text_kb_result = self.text_kb_manager.stage_document(
            filepath,
            filename=filename,
            domain=self.focus_domain,
            source_label="upload",
        )
        added = self._auto_vectorize(content)
        return {
            "success": True,
            "doc_id": doc_id,
            "filename": filename,
            "content_length": len(content),
            "entries_added": added,
            "text_kb": text_kb_result,
        }

    def sync_uploads(self):
        self.text_kb_manager.ensure_workspace(self.focus_domain)
        synced = 0
        skipped = 0
        removed = 0
        existing_docs = self.db.list_documents()
        valid_paths = set()

        for root, _, files in os.walk(self.upload_dir):
            for name in files:
                path = os.path.abspath(os.path.join(root, name))
                valid_paths.add(path)
                ext = os.path.splitext(name)[1].lower()
                if ext not in self.SUPPORTED_TEXT_EXTENSIONS:
                    skipped += 1
                    continue
                existing = self.db.get_document_by_filepath(path)
                if existing:
                    continue
                result = self.process_file(path, name)
                if result.get("success"):
                    synced += 1
                else:
                    skipped += 1

        for doc in existing_docs:
            path = os.path.abspath(doc.get("filepath", ""))
            if path and path not in valid_paths and not os.path.exists(path):
                self.db.delete_document(doc["id"])
                removed += 1

        return {"synced": synced, "skipped": skipped, "removed": removed}

    def _extract_text(self, filepath, ext):
        try:
            if ext in self.SUPPORTED_TEXT_EXTENSIONS:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            return "[unsupported]"
        except Exception:
            return "[error]"

    def _auto_vectorize(self, content):
        added = 0
        terms = set(re.findall(r"[\u4e00-\u9fffA-Za-z]{2,16}", content))
        skip = {
            "但是",
            "因为",
            "所以",
            "如果",
            "而且",
            "或者",
            "虽然",
            "然后",
            "因此",
            "可以",
            "可能",
            "需要",
        }
        terms = terms - skip
        for term in list(terms)[:20]:
            domain = self._guess_domain(term)
            if self.db.add_entry(name=term, domain=domain):
                added += 1
        return added

    def _guess_domain(self, term):
        for kw in ["细胞", "蛋白", "基因", "受体", "DNA", "RNA", "膜", "信号"]:
            if kw in term:
                return "biology"
        for kw in ["反应", "分子", "催化", "合成", "酸", "碱", "氧化", "还原"]:
            if kw in term:
                return "chemistry"
        for kw in ["纳米", "晶体", "薄膜", "材料", "合金", "石墨"]:
            if kw in term:
                return "materials"
        return "general"
