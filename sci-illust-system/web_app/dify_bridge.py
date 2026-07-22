
import json, requests, os

class DifyBridge:
    def __init__(self, api_key=None, base_url=None):
        self.api_key = api_key or os.environ.get("DIFY_API_KEY", "")
        self.base_url = base_url or os.environ.get("DIFY_BASE_URL", "http://localhost:8080/api")

    @property
    def is_configured(self):
        return bool(self.api_key and self.base_url)

    def chat(self, query, user="admin"):
        if not self.is_configured:
            return None
        try:
            r = requests.post(self.base_url + "/chat-messages", json={"query": query, "user": user, "response_mode": "blocking"}, headers={"Authorization": "Bearer " + self.api_key}, timeout=60)
            return r.json().get("answer") if r.status_code == 200 else None
        except Exception:
            return None

    def test_connection(self):
        if not self.is_configured:
            return {"status": "not_configured", "message": "no config"}
        try:
            r = requests.get(self.base_url + "/datasets", headers={"Authorization": "Bearer " + self.api_key}, timeout=10)
            return {"status": "ok" if r.status_code == 200 else "error", "message": "HTTP " + str(r.status_code)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
