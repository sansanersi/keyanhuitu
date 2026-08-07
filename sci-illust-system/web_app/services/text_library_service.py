"""文本库聚合服务。"""


class TextLibraryService:
    """把知识条目、文档和文本检索能力收束到文本库边界。"""

    def __init__(self, catalog_service, document_service, search_service):
        self.catalog_service = catalog_service
        self.document_service = document_service
        self.search_service = search_service

    def dashboard(self):
        entries = self.catalog_service.list_entries(domain="", search="")
        documents = self.document_service.list_documents()
        text_kb_status = self.document_service.text_kb_status()
        entry_items = entries.get("entries", [])
        document_items = documents.get("documents", [])
        return {
            "boundary": "text_library",
            "entries_total": entries.get("total", len(entry_items)),
            "documents_total": len(document_items),
            "entries": entry_items,
            "documents": document_items,
            "text_kb_status": text_kb_status,
        }

    def search(self, query):
        return self.search_service.search(query)
