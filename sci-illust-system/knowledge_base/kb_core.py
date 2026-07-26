import json, os, re
from typing import Dict, List, Optional

def _data_dir():
    d = os.path.join(os.path.dirname(__file__), "..", "data")
    return d if os.path.isdir(d) else os.path.join(os.path.dirname(__file__), "data")

class VectorStore:
    def __init__(self):
        self.vectors = []
    def add(self, iid, vec):
        self.vectors.append((iid, vec))
    def search(self, qv, top_k=5):
        def dot(a, b): return sum(x*y for x,y in zip(a,b))
        def norm(a): return sum(x*x for x in a)**0.5
        scores = []
        for iid, v in self.vectors:
            s = dot(qv, v) / (norm(qv) * norm(v) + 1e-10)
            scores.append((iid, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    @property
    def size(self): return len(self.vectors)

class TextEmbedding:
    def __init__(self, vs=256):
        self.vs = vs
        self.w2i = {}
    def _tok(self, t):
        return re.findall(r"[\w\u4e00-\u9fff]+", t.lower())
    def build(self, texts):
        idx = 0
        for t in texts:
            for tok in self._tok(t):
                if tok not in self.w2i and idx < self.vs:
                    self.w2i[tok] = idx
                    idx += 1
    def embed(self, text):
        vec = [0.0] * self.vs
        for tok in self._tok(text):
            if tok in self.w2i:
                vec[self.w2i[tok]] += 1.0
        n = sum(v*v for v in vec)**0.5
        return [v/n for v in vec] if n > 0 else vec

class DomainVocabulary:
    def __init__(self, data_path=None, allowed_domains=None):
        self.data = {"domains": {}}
        self._all = []; self._tm = {}
        self.allowed_domains = set(allowed_domains or [])
        if data_path and os.path.exists(data_path):
            self.load(data_path)
    def load(self, path):
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._idx()
    def _idx(self):
        self._all = []; self._tm = {}
        for dk, dv in self.data.get("domains", {}).items():
            if self.allowed_domains and dk not in self.allowed_domains:
                continue
            for ck, cv in dv.get("element_categories", {}).items():
                for e in cv.get("elements", []):
                    n = e["name"]
                    self._all.append(n)
                    self._tm[n] = {"domain": dk, "domain_name": dv["name"], "category": cv["name"],
                                   "english": e["english"], "type": e["type"], "shape": e["shape"],
                                   "color_scheme": e["color_scheme"], "tags": e.get("tags", [])}
    def search(self, q, top_k=10):
        ql = q.lower(); res = []
        for t, m in self._tm.items():
            s = 0.0
            if ql in t.lower(): s += 1.0
            if ql in m["english"].lower(): s += 0.8
            for tag in m.get("tags", []):
                if ql in tag.lower(): s += 0.5
            if s > 0: res.append((t, s, m))
        res.sort(key=lambda x: x[1], reverse=True)
        return res[:top_k]
    def get(self, name):
        return self._tm.get(name)
    @property
    def all_terms(self): return self._all.copy()
    @property
    def domains(self):
        domains = list(self.data.get("domains", {}).keys())
        if self.allowed_domains:
            domains = [domain for domain in domains if domain in self.allowed_domains]
        return domains
    @property
    def stats(self):
        return {"total_terms": len(self._all), "domains": self.domains,
                "domain_breakdown": {d: len([t for t,m in self._tm.items() if m["domain"]==d]) for d in self.domains}}

class KnowledgeBase:
    def __init__(self, vocab_path=None, color_scheme_path=None, focus_domain=None, corpus_paths=None):
        self._dd = _data_dir()
        self.focus_domain = self._normalize_domain(focus_domain or os.environ.get("SCI_FOCUS_DOMAIN", "biology"))
        self.vocabulary = DomainVocabulary(
            vocab_path or os.path.join(self._dd, "domain_vocab.json"),
            allowed_domains=[self.focus_domain] if self.focus_domain else [],
        )
        self.vs = VectorStore(); self.emb = TextEmbedding()
        self._entries = []
        self._corpus_entries = []
        self._corpus_vs = VectorStore()
        self._corpus_emb = TextEmbedding()
        self.corpus_paths = self._resolve_corpus_paths(corpus_paths)
        self._build()
        self._build_corpus()

    def _normalize_domain(self, value):
        value = str(value or "").strip().lower()
        if not value:
            return ""
        aliases = {
            "bio": "biology",
            "biological": "biology",
            "cell": "biology",
            "life_science": "biology",
        }
        return aliases.get(value, value)

    def _resolve_corpus_paths(self, corpus_paths):
        if corpus_paths is None:
            domain = self.focus_domain or "biology"
            candidates = [
                os.path.join(self._dd, "corpus", domain),
                os.path.join(os.path.dirname(__file__), "..", "web_app", "data", "corpus", domain),
            ]
            return [path for path in candidates if os.path.isdir(path)]
        if isinstance(corpus_paths, str):
            corpus_paths = [corpus_paths]
        return [path for path in corpus_paths if os.path.isdir(path)]

    def _build(self):
        for t in self.vocabulary.all_terms:
            m = self.vocabulary.get(t)
            if m:
                txt = f"{t} {m['english']} {' '.join(m.get('tags',[]))}"
                self._entries.append({"term": t, "text": txt, "metadata": m})
        self.emb.build([e["text"] for e in self._entries])
        for e in self._entries:
            self.vs.add(e["term"], self.emb.embed(e["text"]))

    def _build_corpus(self):
        for path in self.corpus_paths:
            self._load_corpus_path(path)
        self._corpus_emb.build([e["text"] for e in self._corpus_entries])
        for index, entry in enumerate(self._corpus_entries):
            self._corpus_vs.add("corpus_" + str(index), self._corpus_emb.embed(entry["text"]))

    def _load_corpus_path(self, root):
        for current_root, _, files in os.walk(root):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                path = os.path.join(current_root, file)
                try:
                    if ext in (".txt", ".md"):
                        self._corpus_entries.append(self._corpus_from_text(path))
                    elif ext == ".json":
                        self._corpus_entries.extend(self._corpus_from_json(path))
                except Exception:
                    continue

    def _corpus_from_text(self, path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        title = os.path.splitext(os.path.basename(path))[0]
        domain = self.focus_domain or "biology"
        return {
            "id": path,
            "term": title,
            "title": title,
            "text": title + " " + content,
            "content": content,
            "metadata": {
                "domain": domain,
                "category": "corpus",
                "english": title,
                "type": "corpus",
                "shape": "rounded_rect",
                "color_scheme": ["#64748B"],
                "tags": [domain, "corpus"],
                "source": "text_corpus",
                "path": path,
            },
        }

    def _corpus_from_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data if isinstance(data, list) else data.get("entries") or data.get("items") or []
        results = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or f"entry_{index}").strip()
            content = str(item.get("content") or item.get("text") or item.get("summary") or "").strip()
            domain = self._normalize_domain(item.get("domain") or self.focus_domain or "biology")
            tags = item.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            results.append({
                "id": path + "#" + str(index),
                "term": title,
                "title": title,
                "text": title + " " + content + " " + " ".join([str(tag) for tag in tags]),
                "content": content,
                "metadata": {
                    "domain": domain,
                    "category": str(item.get("category") or "corpus"),
                    "english": str(item.get("english") or title),
                    "type": "corpus",
                    "shape": "rounded_rect",
                    "color_scheme": ["#64748B"],
                    "tags": tags,
                    "source": "json_corpus",
                    "path": path,
                },
            })
        return results
    def query(self, text, top_k=8):
        res, seen = [], set()
        if self.vs.size > 0:
            qv = self.emb.embed(text)
            for t, s in self.vs.search(qv, top_k):
                m = self.vocabulary.get(t)
                if m and t not in seen:
                    res.append({"term": t, "score": round(s, 3), "metadata": m, "source": "vector"})
                    seen.add(t)
        for t, s, m in self.vocabulary.search(text, top_k):
            if t not in seen:
                res.append({"term": t, "score": round(s/5, 3), "metadata": m, "source": "keyword"})
                seen.add(t)
        if self._corpus_vs.size > 0:
            qv = self._corpus_emb.embed(text)
            for iid, s in self._corpus_vs.search(qv, min(top_k, 4)):
                index = int(iid.split("_", 1)[1])
                entry = self._corpus_entries[index]
                res.append({
                    "term": entry["term"],
                    "score": round(s / 3, 3),
                    "metadata": entry["metadata"],
                    "source": "corpus",
                    "content": entry["content"],
                })
        res.sort(key=lambda x: x["score"], reverse=True)
        return res[:top_k]
    def get_term(self, name):
        return self.vocabulary.get(name)
    def get_terms_by_domain(self, d):
        return [{"term": t, "metadata": m} for t, m in self.vocabulary._tm.items() if m["domain"] == d]
    def get_domain_info(self, d):
        return self.vocabulary.data.get("domains", {}).get(d)
    def get_context_snippets(self, text, top_k=3):
        snippets = []
        if self._corpus_vs.size == 0:
            return snippets
        qv = self._corpus_emb.embed(text)
        for iid, score in self._corpus_vs.search(qv, top_k):
            index = int(iid.split("_", 1)[1])
            entry = self._corpus_entries[index]
            content = entry.get("content", "")
            preview = content[:220].replace("\n", " ").strip()
            if len(content) > 220:
                preview += "..."
            snippets.append({
                "title": entry.get("title", entry.get("term", "")),
                "preview": preview,
                "score": round(score, 3),
                "source": entry.get("metadata", {}).get("source", "text_corpus"),
                "path": entry.get("metadata", {}).get("path", ""),
            })
        return snippets
    @property
    def stats(self):
        s = self.vocabulary.stats
        return {
            **s,
            "focus_domain": self.focus_domain,
            "corpus_documents": len(self._corpus_entries),
            "vector_index_size": self.vs.size,
        }
    def __repr__(self):
        s = self.stats
        return f"<KnowledgeBase: {s['total_terms']} terms, {len(s['domains'])} domains>"
