
import json
import os
import sqlite3
from contextlib import closing
from typing import Dict, List


def _default_db_path():
    configured = os.environ.get("SCI_WEBAPP_DB_PATH", "").strip()
    if configured:
        return os.path.abspath(configured)
    return os.path.join(os.path.dirname(__file__), "data", "knowledge.db")


def logical_database_config():
    """读取未来 MySQL 三逻辑库配置；当前阶段只做配置抽象，不建立连接。"""

    return {
        "host": os.environ.get("SCI_MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("SCI_MYSQL_PORT", "3306")),
        "user": os.environ.get("SCI_MYSQL_USER", "root"),
        "password": os.environ.get("SCI_MYSQL_PASSWORD", ""),
        "schemas": {
            "text": os.environ.get("SCI_TEXT_DB_NAME", "text_db"),
            "image": os.environ.get("SCI_IMAGE_DB_NAME", "image_db"),
            "app": os.environ.get("SCI_APP_DB_NAME", "app_db"),
        },
    }


DB_PATH = _default_db_path()

class KnowledgeDatabase:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
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
            conn.commit()

    def add_entry(self, name, english="", domain="", category="", shape="", color_scheme=None, tags=None, description=""):
        cs = json.dumps(color_scheme or [])
        tg = json.dumps(tags or [])
        with closing(sqlite3.connect(self.db_path)) as conn:
            try:
                conn.execute("INSERT INTO entries (name, english, domain, category, shape, color_scheme, tags, description) VALUES (?,?,?,?,?,?,?,?)",
                             (name, english, domain, category, shape, cs, tg, description))
                conn.commit()
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
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("UPDATE entries SET " + ", ".join(fields) + ", updated_at=CURRENT_TIMESTAMP WHERE id=?", values)
            conn.commit()

    def delete_entry(self, eid):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("DELETE FROM entries WHERE id=?", (eid,))
            conn.commit()

    def list_entries(self, domain="", search="", limit=100, offset=0):
        with closing(sqlite3.connect(self.db_path)) as conn:
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
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("INSERT INTO documents (filename, filepath, file_type, content) VALUES (?,?,?,?)", (filename, filepath, file_type, content))
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_document_by_filepath(self, filepath):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM documents WHERE filepath=?", (filepath,)).fetchone()
            return dict(row) if row else None

    def save_document(self, filename, filepath, file_type="", content="", vectorized=0):
        existing = self.get_document_by_filepath(filepath)
        with closing(sqlite3.connect(self.db_path)) as conn:
            if existing:
                conn.execute(
                    "UPDATE documents SET filename=?, file_type=?, content=?, vectorized=? WHERE id=?",
                    (filename, file_type, content, vectorized, existing["id"]),
                )
                conn.commit()
                return existing["id"]
            conn.execute(
                "INSERT INTO documents (filename, filepath, file_type, content, vectorized) VALUES (?,?,?,?,?)",
                (filename, filepath, file_type, content, vectorized),
            )
            conn.commit()
            return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_document_vector(self, did, content, vectorized=1):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("UPDATE documents SET content=?, vectorized=? WHERE id=?", (content, vectorized, did))
            conn.commit()

    def list_documents(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def delete_document(self, did):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("DELETE FROM documents WHERE id=?", (did,))
            conn.commit()

    def get_setting(self, key, default=""):
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def set_setting(self, key, value):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
            conn.commit()

    def list_settings(self, prefix=""):
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if prefix:
                rows = conn.execute("SELECT * FROM settings WHERE key LIKE ? ORDER BY key", (prefix + "%",)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM settings ORDER BY key").fetchall()
            return {row["key"]: row["value"] for row in rows}

    @property
    def stats(self):
        with closing(sqlite3.connect(self.db_path)) as conn:
            e = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            d = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            v = conn.execute("SELECT COUNT(*) FROM documents WHERE vectorized=1").fetchone()[0]
            dm = conn.execute("SELECT domain, COUNT(*) FROM entries WHERE domain!='' GROUP BY domain").fetchall()
            return {"entries": e, "documents": d, "vectorized_documents": v, "domains": {r[0]: r[1] for r in dm}}
