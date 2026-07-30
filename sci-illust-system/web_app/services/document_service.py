import os


"""Document and text knowledge base orchestration."""


class DocumentService:
    def __init__(self, database, processor, text_kb_manager, focus_domain):
        self.db = database
        self.processor = processor
        self.text_kb = text_kb_manager
        self.focus_domain = focus_domain

    def _resolve(self, value):
        return value() if callable(value) else value

    def upload_document(self, file_storage):
        if file_storage is None:
            return {"success": False, "error": "missing_file"}
        if file_storage.filename == "":
            return {"success": False, "error": "empty_filename"}

        processor = self._resolve(self.processor)
        path = os.path.join(processor.upload_dir, file_storage.filename)
        file_storage.save(path)
        return processor.process_file(path, file_storage.filename)

    def sync_uploaded_documents(self):
        return self._resolve(self.processor).sync_uploads()

    def list_documents(self):
        self.sync_uploaded_documents()
        return {"documents": self._resolve(self.db).list_documents()}

    def text_kb_status(self):
        self.sync_uploaded_documents()
        return self._resolve(self.text_kb).status(self.focus_domain)

    def init_text_kb(self, initialize_cli=False, force=False):
        return self._resolve(self.text_kb).ensure_workspace(
            self.focus_domain,
            initialize_cli=initialize_cli,
            force=force,
        )
