
import os, re
from database import KnowledgeDatabase

class DocumentProcessor:
    def __init__(self, upload_dir=None):
        self.upload_dir = upload_dir or os.path.join(os.path.dirname(__file__), "data", "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)
        self.db = KnowledgeDatabase()

    def process_file(self, filepath, filename=None):
        filename = filename or os.path.basename(filepath)
        ext = os.path.splitext(filename)[1].lower()
        content = self._extract_text(filepath, ext)
        if not content:
            return {"success": False, "error": "no content"}
        doc_id = self.db.add_document(filename, filepath, ext, content)
        added = self._auto_vectorize(content)
        self.db.update_document_vector(doc_id, content, 1)
        return {"success": True, "doc_id": doc_id, "filename": filename, "content_length": len(content), "entries_added": added}

    def _extract_text(self, filepath, ext):
        try:
            if ext in (".txt", ".md", ".csv", ".json"):
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            return "[unsupported]"
        except Exception:
            return "[error]"

    def _auto_vectorize(self, content):
        added = 0
        terms = set(re.findall(r"[一-鿿]{2,6}", content))
        skip = {"但是", "因为", "所以", "如果", "而且", "或者", "虽然", "然后", "因此", "可以", "可能", "需要"}
        terms = terms - skip
        for term in list(terms)[:20]:
            d = self._guess_domain(term)
            if self.db.add_entry(name=term, domain=d):
                added += 1
        return added

    def _guess_domain(self, term):
        for kw in ["细胞","蛋白","基因","受体","DNA","RNA","膜","信号"]:
            if kw in term: return "biology"
        for kw in ["反应","分子","催化","合成","酸","碱","氧化","还原"]:
            if kw in term: return "chemistry"
        for kw in ["纳米","晶体","薄膜","材料","合金","石墨"]:
            if kw in term: return "materials"
        return "general"
