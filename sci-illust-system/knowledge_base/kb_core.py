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
    def __init__(self, data_path=None):
        self.data = {"domains": {}}
        self._all = []; self._tm = {}
        if data_path and os.path.exists(data_path):
            self.load(data_path)
    def load(self, path):
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self._idx()
    def _idx(self):
        self._all = []; self._tm = {}
        for dk, dv in self.data.get("domains", {}).items():
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
    def domains(self): return list(self.data.get("domains", {}).keys())
    @property
    def stats(self):
        return {"total_terms": len(self._all), "domains": self.domains,
                "domain_breakdown": {d: len([t for t,m in self._tm.items() if m["domain"]==d]) for d in self.domains}}

class KnowledgeBase:
    def __init__(self, vocab_path=None, color_scheme_path=None):
        self._dd = _data_dir()
        self.vocabulary = DomainVocabulary(vocab_path or os.path.join(self._dd, "domain_vocab.json"))
        self.vs = VectorStore(); self.emb = TextEmbedding()
        self._entries = []; self._build()
    def _build(self):
        for t in self.vocabulary.all_terms:
            m = self.vocabulary.get(t)
            if m:
                txt = f"{t} {m['english']} {' '.join(m.get('tags',[]))}"
                self._entries.append({"term": t, "text": txt, "metadata": m})
        self.emb.build([e["text"] for e in self._entries])
        for e in self._entries:
            self.vs.add(e["term"], self.emb.embed(e["text"]))
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
        res.sort(key=lambda x: x["score"], reverse=True)
        return res[:top_k]
    def get_term(self, name):
        return self.vocabulary.get(name)
    def get_terms_by_domain(self, d):
        return [{"term": t, "metadata": m} for t, m in self.vocabulary._tm.items() if m["domain"] == d]
    def get_domain_info(self, d):
        return self.vocabulary.data.get("domains", {}).get(d)
    @property
    def stats(self):
        s = self.vocabulary.stats
        return {**s, "vector_index_size": self.vs.size}
    def __repr__(self):
        s = self.stats
        return f"<KnowledgeBase: {s['total_terms']} terms, {len(s['domains'])} domains>"
