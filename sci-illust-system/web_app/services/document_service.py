"""Document and text knowledge base orchestration."""


class DocumentService:
    def __init__(self, database, processor, text_kb_manager, focus_domain):
        self.db = database
        self.processor = processor
        self.text_kb = text_kb_manager
        self.focus_domain = focus_domain

    def sync_uploaded_documents(self):
        return self.processor.sync_uploads()

    def list_documents(self):
        self.sync_uploaded_documents()
        return {"documents": self.db.list_documents()}

    def text_kb_status(self):
        self.sync_uploaded_documents()
        return self.text_kb.status(self.focus_domain)

    def init_text_kb(self, initialize_cli=False, force=False):
        return self.text_kb.ensure_workspace(
            self.focus_domain,
            initialize_cli=initialize_cli,
            force=force,
        )
