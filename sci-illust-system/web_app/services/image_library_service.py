"""图片库聚合服务。"""


class ImageLibraryService:
    """把图元、Bioicons 和图片资产能力收束到图片库边界。"""

    def __init__(self, catalog_service):
        self.catalog_service = catalog_service

    def dashboard(self):
        return {
            "boundary": "image_library",
            "sources": ["local_files", "mysql_metadata", "bioicons", "image_graph"],
            "bioicons_status": self.catalog_service.bioicons_status(),
        }

    def suggest_assets(self, query, top_k=8):
        query_text = (query or "").strip()
        elements = self.catalog_service.suggest_elements(query_text, top_k=top_k)
        bioicons = self.catalog_service.suggest_bioicons(query_text, top_k=top_k)
        items = []
        items.extend(elements.get("elements", []))
        items.extend(bioicons.get("icons", []))
        return {
            "boundary": "image_library",
            "query": query_text,
            "items": items,
            "total": len(items),
            "bioicons_status": bioicons.get("stats", {}),
        }
