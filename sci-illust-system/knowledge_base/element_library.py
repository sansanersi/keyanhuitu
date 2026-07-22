from typing import Dict, List, Optional
from .kb_core import DomainVocabulary

class ElementTemplate:
    def __init__(self, name="", english_name="", domain="", category="", shape="",
                 color_scheme=None, default_size=None, type="generic", tags=None, description=""):
        self.name = name; self.english_name = english_name; self.domain = domain
        self.category = category; self.shape = shape; self.color_scheme = color_scheme or ["#3498DB"]
        self.default_size = default_size or {"width": 60, "height": 60}
        self.type = type; self.tags = tags or []; self.description = description or name
    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}
    @classmethod
    def from_meta(cls, name, meta):
        return cls(name=name, english_name=meta.get("english", ""), domain=meta.get("domain", ""),
                   category=meta.get("category", ""), shape=meta.get("shape", ""),
                   color_scheme=meta.get("color_scheme"), type=meta.get("type", "generic"),
                   tags=meta.get("tags", []), description=f"{meta.get('domain','')}/{meta.get('category','')} - {name}")

class ElementLibrary:
    def __init__(self, vocabulary=None):
        self._templates = {}; self._domain_idx = {}; self._tag_idx = {}
        if vocabulary: self.build(vocabulary)
    def build(self, vocab):
        for t in vocab.all_terms:
            m = vocab.get(t)
            if m: self._reg(ElementTemplate.from_meta(t, m))
        return self
    def _reg(self, t):
        self._templates[t.name] = t
        self._domain_idx.setdefault(t.domain, []).append(t.name)
        for tag in t.tags: self._tag_idx.setdefault(tag, []).append(t.name)
    def get(self, name):
        return self._templates.get(name)
    def suggest(self, text, top_k=5):
        t = text.lower(); scored = []
        for n, tmp in self._templates.items():
            s = 0.0
            if t in n.lower(): s += 3.0
            if t in tmp.english_name.lower(): s += 2.0
            for tag in tmp.tags:
                if t in tag.lower(): s += 1.0
            if s > 0: scored.append((tmp, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [x[0] for x in scored[:top_k]]

# Verify
if __name__ == "__main__":
    kb = KnowledgeBase()
    print(kb)
