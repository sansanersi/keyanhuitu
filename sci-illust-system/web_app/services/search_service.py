"""Search orchestration for keyword KB and text KB."""


class SearchService:
    def __init__(self, knowledge_base, text_kb_manager, focus_domain):
        self.kb = knowledge_base
        self.text_kb = text_kb_manager
        self.focus_domain = focus_domain

    def search(self, query):
        query_text = (query or "").strip()
        results = self.kb.query(query_text, top_k=10)
        snippets = self.kb.get_context_snippets(query_text, top_k=3) if query_text else []
        text_kb_status = self.text_kb.status(self.focus_domain)
        text_kb_result = self.text_kb.query(query_text, domain=self.focus_domain) if query_text else {
            "available": False,
            "query": "",
            "method": "local",
            "answer": "",
            "error": "empty query",
        }
        return {
            "results": results,
            "snippets": snippets,
            "text_kb": text_kb_result,
            "text_kb_status": text_kb_status,
        }
