from copy import deepcopy


class AssetResolver:
    def __init__(self, element_library=None, bioicons=None, max_matches=3):
        self.element_library = element_library
        self.bioicons = bioicons
        self.max_matches = max_matches

    def resolve_workflow(self, workflow):
        resolved = deepcopy(workflow)
        elements = resolved.get("elements", [])
        if not isinstance(elements, list):
            return resolved

        for element in elements:
            if not isinstance(element, dict):
                continue
            matches = self.resolve_element(element)
            element["asset_matches"] = matches
            element["selected_asset"] = matches[0] if matches else None
        return resolved

    def resolve_element(self, element):
        matches = []
        query = self._query(element)
        matches.extend(self._element_library_matches(query))
        matches.extend(self._bioicon_matches(query))
        if not matches:
            matches.append(self._hint_match(element))
        matches.sort(key=lambda item: (self._source_priority(item.get("source")), item.get("score", 0)), reverse=True)
        return matches[: self.max_matches]

    def _element_library_matches(self, query):
        if not self.element_library or not hasattr(self.element_library, "suggest"):
            return []
        matches = []
        for template in self.element_library.suggest(query, top_k=self.max_matches):
            data = template.to_dict() if hasattr(template, "to_dict") else dict(template)
            matches.append(
                {
                    "source": "element_library",
                    "name": data.get("name", ""),
                    "english_name": data.get("english_name", ""),
                    "category": data.get("category", ""),
                    "shape": data.get("shape", "rounded_rect"),
                    "color_scheme": data.get("color_scheme", []),
                    "default_size": data.get("default_size", {}),
                    "score": 0.8,
                }
            )
        return matches

    def _bioicon_matches(self, query):
        if not self.bioicons or not getattr(self.bioicons, "available", False):
            return []
        matches = []
        for item in self.bioicons.suggest(query, top_k=self.max_matches):
            matches.append(
                {
                    "source": "bioicons",
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "shape": "icon",
                    "svg_path": item.get("svg_path", ""),
                    "score": float(item.get("score", 0.6) or 0.6),
                }
            )
        return matches

    def _hint_match(self, element):
        hint = element.get("asset_hint") if isinstance(element.get("asset_hint"), dict) else {}
        return {
            "source": "workflow_hint",
            "name": element.get("name", element.get("id", "")),
            "shape": hint.get("shape", "rounded_rect"),
            "color_scheme": hint.get("color_scheme", []),
            "score": 0.1,
        }

    def _query(self, element):
        hint = element.get("asset_hint") if isinstance(element.get("asset_hint"), dict) else {}
        parts = [
            element.get("name", ""),
            element.get("category", ""),
            element.get("visual_prompt", ""),
            hint.get("english", ""),
            hint.get("shape", ""),
        ]
        return " ".join([str(part) for part in parts if part])

    def _source_priority(self, source):
        priorities = {"element_library": 3, "bioicons": 2, "workflow_hint": 1}
        return priorities.get(source, 0)
