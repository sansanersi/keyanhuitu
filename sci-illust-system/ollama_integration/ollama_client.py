import json, os, re
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request, urllib.error

class OllamaClient:
    def __init__(self, base_url="http://127.0.0.1:11434", default_model="qwen3.5:4b", timeout=120):
        self.base_url = self._normalize_base_url(base_url); self.default_model = default_model; self.timeout = timeout
        self._available_models = []; self._refresh()

    def _req(self, method, path, data=None):
        import json as j
        url = self.base_url + path
        body = j.dumps(data).encode("utf-8") if data else None
        headers = {"Content-Type": "application/json"} if body else {}
        if HAS_REQUESTS:
            try:
                r = getattr(requests, method)(url, json=data, headers=headers, timeout=self.timeout)
                return r.json() if r.status_code == 200 else None
            except: return None
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method.upper())
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return j.loads(r.read().decode("utf-8"))
        except: return None

    def _get_response(self, r):
        if not r: return None
        if "response" in r and r["response"]: return r
        if "message" in r and r["message"].get("content"): return r
        if "message" in r and r["message"].get("thinking"):
            r["message"]["content"] = r["message"]["thinking"]; return r
        if "thinking" in r and r["thinking"]:
            r["response"] = r["thinking"]; return r
        return r

    def _refresh(self):
        r = self._req("get", "/api/tags")
        self._available_models = [m["name"] for m in r.get("models", [])] if r else []

    @property
    def is_available(self): return self._req("get", "/api/tags") is not None
    def has_model(self, n): return n in self._available_models
    def list_models(self):
        self._refresh(); return self._available_models.copy()

    def chat(self, messages, model=None, temperature=0.1, max_tokens=2048):
        model = model or self.default_model
        if model not in self._available_models: return None
        r = self._req("post", "/api/chat", {"model":model, "messages":messages, "stream":False,
            "options":{"temperature":temperature, "num_predict":max_tokens}})
        resp = self._get_response(r)
        if resp and "message" in resp and resp["message"].get("content"):
            return resp["message"]["content"]
        return None

    def generate(self, prompt, model=None, temperature=0.1, max_tokens=2048, system=None):
        msgs = []
        if system: msgs.append({"role":"system","content":system})
        msgs.append({"role":"user","content":prompt})
        return self.chat(msgs, model, temperature, max_tokens)

    def _normalize_base_url(self, base_url):
        url = (base_url or "").strip().rstrip("/")
        if url.endswith("/api"):
            return url[:-4]
        if url.endswith("/v1"):
            return url[:-3]
        return url or "http://127.0.0.1:11434"
