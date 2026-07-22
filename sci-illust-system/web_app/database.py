
import json, os, sqlite3
from typing import Dict, List

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "knowledge.db")

class KnowledgeDatabase:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL, english TEXT DEFAULT "",
                    domain TEXT DEFAULT "", category TEXT DEFAULT "",
                    shape TEXT DEFAULT "", color_scheme TEXT DEFAULT "[]",
                    tags TEXT DEFAULT "[]", description TEXT DEFAULT "",
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL, filepath TEXT NOT NULL,
                    file_type TEXT DEFAULT "", content TEXT DEFAULT "",
                    vectorized INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
            """)

    def add_entry(self, name, english="", domain="", category="", shape="", color_scheme=None, tags=None, description=""):
        cs = json.dumps(color_scheme or [])
        tg = json.dumps(tags or [])
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("INSERT INTO entries (name, english, domain, category, shape, color_scheme, tags, description) VALUES (?,?,?,?,?,?,?,?)",
                             (name, english, domain, category, shape, cs, tg, description))
                return True
            except sqlite3.IntegrityError:
                return False

    def update_entry(self, eid, **kwargs):
        fields, values = [], []
        for k, v in kwargs.items():
            if k in ("color_scheme", "tags") and isinstance(v, (list, dict)):
                v = json.dumps(v)
            fields.append(k + "=?")
            values.append(v)
        values.append(eid)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE entries SET " + ", ".join(fields) + ", updated_at=CURRENT_TIMESTAMP WHERE id=?", values)

    def delete_entry(self, eid):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM entries WHERE id=?", (eid,))

    def list_entries(self, domain="", search="", limit=100, offset=0):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            where, params = [], []
            if domain:
                where.append("domain=?")
                params.append(domain)
            if search:
                s = "%" + search + "%"
                where.append("(name LIKE ? OR english LIKE ? OR tags LIKE ?)")
                params.extend([s, s, s])
            w = "WHERE " + " AND ".join(where) if where else ""
            rows = conn.execute("SELECT * FROM entries " + w + " ORDER BY updated_at DESC LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM entries " + w, params).fetchone()[0]
            return [dict(r) for r in rows], total

    def add_document(self, filename, filepath, file_type="", content=""):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO documents (filename, filepath, file_type, content) VALUES (?,?,?,?)", (filename, filepath, file_type, content))
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_document_vector(self, did, content, vectorized=1):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE documents SET content=?, vectorized=? WHERE id=?", (content, vectorized, did))

    def list_documents(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def delete_document(self, did):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM documents WHERE id=?", (did,))

    @property
    def stats(self):
        with sqlite3.connect(self.db_path) as conn:
            e = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            d = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            v = conn.execute("SELECT COUNT(*) FROM documents WHERE vectorized=1").fetchone()[0]
            dm = conn.execute("SELECT domain, COUNT(*) FROM entries WHERE domain!='' GROUP BY domain").fetchall()
            return {"entries": e, "documents": d, "vectorized_documents": v, "domains": {r[0]: r[1] for r in dm}}
