import json
import os
import re


class BioiconTemplate:
    def __init__(self, name="", category="", license="", author="", svg_path="", description=""):
        self.name = name
        self.english_name = name
        self.domain = "bioicons"
        self.category = category
        self.shape = "icon"
        self.color_scheme = ["#4A90D9"]
        self.default_size = {"width": 72, "height": 72}
        self.type = "bioicon"
        self.tags = self._build_tags(name, category, license, author)
        self.description = description or category or name
        self.license = license
        self.author = author
        self.svg_path = svg_path

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    def _build_tags(self, name, category, license, author):
        parts = [name, category, license, author]
        tags = []
        for part in parts:
            for token in re.findall(r"[\w\u4e00-\u9fff]+", str(part).lower()):
                if token not in tags:
                    tags.append(token)
        return tags


class BioiconsLibrary:
    def __init__(self, root_path=""):
        self.root_path = root_path or ""
        self.icons_dir = os.path.join(self.root_path, "static", "icons")
        self.index_path = os.path.join(self.icons_dir, "icons.json")
        self.categories_path = os.path.join(self.icons_dir, "categories.json")
        self._templates = []
        self._by_name = {}
        self._svg_index = {}
        self._categories = {}
        self._category_names = []
        self._load()

    @property
    def available(self):
        return bool(self._templates)

    @property
    def count(self):
        return len(self._templates)

    def _load(self):
        if not os.path.isfile(self.index_path):
            return

        self._categories = self._load_categories()
        self._build_svg_index()

        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            items = []

        for item in items:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            category = str(item.get("category", "")).strip()
            license_name = str(item.get("license", "")).strip()
            author = str(item.get("author", "")).strip()
            svg_path = self._resolve_svg(name, category, license_name, author)
            description = self._description(name, category, license_name, author)
            template = BioiconTemplate(
                name=name,
                category=category,
                license=license_name,
                author=author,
                svg_path=svg_path,
                description=description,
            )
            self._templates.append(template)
            self._by_name[name.lower()] = template

    def _load_categories(self):
        if not os.path.isfile(self.categories_path):
            return {}
        try:
            with open(self.categories_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                if isinstance(data, list):
                    self._category_names = [str(item) for item in data]
                    return {}
                return {}
        except Exception:
            return {}

    def _build_svg_index(self):
        if not os.path.isdir(self.icons_dir):
            return
        for root, _, files in os.walk(self.icons_dir):
            for file in files:
                if not file.lower().endswith(".svg"):
                    continue
                stem = os.path.splitext(file)[0]
                key = self._normalize(stem)
                path = os.path.join(root, file)
                if key and key not in self._svg_index:
                    self._svg_index[key] = path

    def _description(self, name, category, license_name, author):
        category_info = self._categories.get(category, {})
        count = category_info.get("n")
        parts = [category or "bioicon"]
        if count is not None:
            parts.append("共 " + str(count) + " 个")
        if author:
            parts.append(author)
        if license_name:
            parts.append(license_name)
        return " / ".join(parts) + " - " + name

    def _normalize(self, value):
        return re.sub(r"[^a-z0-9]+", "", str(value).lower())

    def _resolve_svg(self, name, category, license_name, author):
        candidates = [
            name,
            self._normalize(name),
            name.replace("_", "-"),
            name.replace("-", "_"),
        ]
        for candidate in candidates:
            path = self._svg_index.get(self._normalize(candidate))
            if path:
                return path

        if not os.path.isdir(self.icons_dir):
            return ""

        candidate_dirs = []
        if license_name:
            candidate_dirs.append(os.path.join(self.icons_dir, license_name, category, author))
            candidate_dirs.append(os.path.join(self.icons_dir, license_name, category))
        candidate_dirs.append(os.path.join(self.icons_dir, category, author))
        candidate_dirs.append(os.path.join(self.icons_dir, category))
        candidate_dirs.append(self.icons_dir)

        seen = set()
        target = self._normalize(name)
        for base in candidate_dirs:
            if not os.path.isdir(base) or base in seen:
                continue
            seen.add(base)
            exact = os.path.join(base, name + ".svg")
            if os.path.isfile(exact):
                return exact
            try:
                for root, _, files in os.walk(base):
                    for file in files:
                        if not file.lower().endswith(".svg"):
                            continue
                        stem = os.path.splitext(file)[0]
                        if self._normalize(stem) == target:
                            return os.path.join(root, file)
            except Exception:
                continue
        return ""

    def suggest(self, text, top_k=8):
        query = text.lower().strip()
        if not query or not self._templates:
            return []

        terms = set(re.findall(r"[\w\u4e00-\u9fff]+", query))
        scored = []
        for template in self._templates:
            score = 0.0
            name_l = template.name.lower()
            category_l = template.category.lower()
            author_l = template.author.lower()
            if query in name_l:
                score += 4.0
            if query in category_l:
                score += 3.0
            if query in author_l:
                score += 1.0
            for term in terms:
                if term in name_l:
                    score += 2.0
                if term in category_l:
                    score += 1.5
                if term in template.tags:
                    score += 0.5
            if score > 0:
                scored.append((score, template))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, template in scored[:top_k]:
            data = template.to_dict()
            data["score"] = round(score, 3)
            results.append(data)
        return results

    def stats(self):
        return {
            "available": self.available,
            "count": self.count,
            "root_path": self.root_path,
            "categories": len(self._categories) or len(self._category_names),
        }
