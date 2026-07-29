"""System-level orchestration for dashboard and Ollama settings."""


class SystemService:
    def __init__(
        self,
        database_getter,
        knowledge_base,
        text_kb_manager,
        bioicons_library,
        focus_domain,
        sync_uploaded_documents,
        get_ollama_models,
        web_mode_getter,
    ):
        self._get_db = database_getter
        self.kb = knowledge_base
        self.text_kb = text_kb_manager
        self.bioicons = bioicons_library
        self.focus_domain = focus_domain
        self.sync_uploaded_documents = sync_uploaded_documents
        self.get_ollama_models = get_ollama_models
        self.web_mode_getter = web_mode_getter

    def dashboard(self):
        self.sync_uploaded_documents()
        stats = self._get_db().stats
        text_kb_status = self.text_kb.status(self.focus_domain)
        return {
            "entries": stats["entries"],
            "documents": stats["documents"],
            "vectorized_documents": stats["vectorized_documents"],
            "domains": stats["domains"],
            "kb_terms": self.kb.stats["total_terms"],
            "kb_vectors": self.kb.stats["vector_index_size"],
            "focus_domain": self.kb.stats.get("focus_domain", self.focus_domain),
            "corpus_documents": self.kb.stats.get("corpus_documents", 0),
            "bioicons_available": self.bioicons.available,
            "bioicons_count": self.bioicons.count,
            "ollama_models": self.get_ollama_models(),
            "text_kb": text_kb_status,
        }

    def ollama_status(self, base_url, default_model):
        models = self.get_ollama_models()
        mode = self.web_mode_getter()
        return {
            "running": len(models) > 0,
            "models": models,
            "base_url": base_url,
            "default_model": default_model,
            "web_mode": mode,
            "server_label": "Flask stable service" if mode == "stable" else "Flask dev service",
        }

    def ollama_config(self, base_url, default_model):
        return {
            "base_url": base_url,
            "default_model": default_model,
            "models": self.get_ollama_models(),
        }

    def update_ollama_config(self, base_url=None, default_model=None):
        database = self._get_db()
        if base_url:
            database.set_setting("ollama_base_url", base_url)
        if default_model:
            database.set_setting("ollama_default_model", default_model)

    def draw_models(self, base_url, default_model):
        return {
            "models": self.get_ollama_models(),
            "default_model": default_model,
            "base_url": base_url,
        }
