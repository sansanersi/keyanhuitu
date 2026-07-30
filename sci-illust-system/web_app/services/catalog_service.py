"""Catalog and suggestion orchestration for web routes."""


class CatalogService:
    def __init__(self, database, knowledge_base, element_library, bioicons_library, focus_domain):
        self.db = database
        self.kb = knowledge_base
        self.el = element_library
        self.bioicons = bioicons_library
        self.focus_domain = focus_domain

    def _resolve(self, value):
        return value() if callable(value) else value

    def list_entries(self, domain="", search=""):
        entries, total = self._resolve(self.db).list_entries(domain=domain, search=search)
        return {"entries": entries, "total": total}

    def add_entry(self, data):
        payload = data or {}
        ok = self._resolve(self.db).add_entry(
            name=payload["name"],
            english=payload.get("english", ""),
            domain=payload.get("domain", ""),
            category=payload.get("category", ""),
            shape=payload.get("shape", ""),
            color_scheme=payload.get("color_scheme", []),
            tags=payload.get("tags", []),
            description=payload.get("description", ""),
        )
        return {"success": ok}

    def update_entry(self, entry_id, data):
        self._resolve(self.db).update_entry(entry_id, **(data or {}))
        return {"success": True}

    def delete_entry(self, entry_id):
        self._resolve(self.db).delete_entry(entry_id)
        return {"success": True}

    def domain_status(self):
        kb = self._resolve(self.kb)
        bioicons = self._resolve(self.bioicons)
        return {
            "focus_domain": kb.stats.get("focus_domain", self.focus_domain),
            "kb_terms": kb.stats["total_terms"],
            "corpus_documents": kb.stats.get("corpus_documents", 0),
            "bioicons_count": bioicons.count,
            "available_domains": kb.vocabulary.domains,
        }

    def suggest_elements(self, text, top_k=8):
        element_library = self._resolve(self.el)
        bioicons = self._resolve(self.bioicons)
        kb_items = []
        for item in element_library.suggest(text, top_k=top_k):
            data = item.to_dict()
            data["source"] = "knowledge_base"
            kb_items.append(data)

        bioicon_items = []
        for item in bioicons.suggest(text, top_k=top_k):
            bioicon_items.append(
                {
                    "name": item.get("name", ""),
                    "english_name": item.get("english_name", ""),
                    "domain": item.get("domain", "bioicons"),
                    "category": item.get("category", ""),
                    "shape": item.get("shape", "icon"),
                    "color_scheme": item.get("color_scheme", ["#4A90D9"]),
                    "description": item.get("description", ""),
                    "type": item.get("type", "bioicon"),
                    "tags": item.get("tags", []),
                    "score": item.get("score", 0),
                    "source": "bioicons",
                    "license": item.get("license", ""),
                    "author": item.get("author", ""),
                    "svg_path": item.get("svg_path", ""),
                }
            )

        merged = []
        seen = set()
        for item in kb_items + bioicon_items:
            key = (item.get("name", "").lower(), item.get("source", ""))
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return {"elements": merged}

    def bioicons_status(self):
        return self._resolve(self.bioicons).stats()

    def suggest_bioicons(self, text, top_k=8):
        bioicons = self._resolve(self.bioicons)
        return {"icons": bioicons.suggest(text, top_k=top_k), "stats": bioicons.stats()}
