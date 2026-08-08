"""数据访问 Repository 边界。

服务器版 v1 先把服务层和具体数据库实现隔开；当前默认实现仍然复用 SQLite。
"""

import os
import json
from typing import Protocol

try:
    from .database import KnowledgeDatabase, logical_database_config
except ImportError:
    from database import KnowledgeDatabase, logical_database_config


class KnowledgeRepository(Protocol):
    @property
    def stats(self):
        ...

    def add_entry(self, name, english="", domain="", category="", shape="", color_scheme=None, tags=None, description=""):
        ...

    def update_entry(self, eid, **kwargs):
        ...

    def delete_entry(self, eid):
        ...

    def list_entries(self, domain="", search="", limit=100, offset=0):
        ...

    def add_document(self, filename, filepath, file_type="", content=""):
        ...

    def get_document_by_filepath(self, filepath):
        ...

    def save_document(self, filename, filepath, file_type="", content="", vectorized=0):
        ...

    def update_document_vector(self, did, content, vectorized=1):
        ...

    def list_documents(self):
        ...

    def delete_document(self, did):
        ...

    def get_setting(self, key, default=""):
        ...

    def set_setting(self, key, value):
        ...

    def list_settings(self, prefix=""):
        ...


class SQLiteKnowledgeRepository(KnowledgeDatabase):
    """SQLite Repository 适配器，保持现有 KnowledgeDatabase 行为兼容。"""


class MySQLKnowledgeRepository:
    """MySQL Repository，映射到服务器版三逻辑库。"""

    def __init__(self, config=None, connector=None):
        self.config = config or logical_database_config()
        self.schemas = self.config["schemas"]
        self.connector = connector or self._load_connector()

    def _load_connector(self):
        try:
            import pymysql
        except ImportError as exc:
            raise RuntimeError("MySQL repository requires PyMySQL. Install requirements first.") from exc
        return pymysql.connect

    def _connect(self):
        return self.connector(
            host=self.config["host"],
            port=self.config["port"],
            user=self.config["user"],
            password=self.config["password"],
            charset="utf8mb4",
            cursorclass=self._dict_cursor_class(),
            autocommit=False,
        )

    def _dict_cursor_class(self):
        try:
            import pymysql

            return pymysql.cursors.DictCursor
        except ImportError:
            return None

    def _table(self, schema_key, table_name):
        return f"{_quote_identifier(self.schemas[schema_key])}.{_quote_identifier(table_name)}"

    def _execute(self, sql, params=None, fetchone=False, fetchall=False):
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                if fetchone:
                    return cursor.fetchone()
                if fetchall:
                    return cursor.fetchall()
                lastrowid = getattr(cursor, "lastrowid", None)
            conn.commit()
            return lastrowid
        finally:
            close = getattr(conn, "close", None)
            if close:
                close()

    @property
    def stats(self):
        entries = self._count(self._table("text", "terms"))
        documents = self._count(self._table("text", "documents"))
        vectorized = self._count(self._table("text", "documents"), "WHERE `vectorized`=1")
        rows = self._execute(
            f"SELECT `domain`, COUNT(*) AS count FROM {self._table('text', 'terms')} "
            "WHERE `domain`!='' GROUP BY `domain`",
            fetchall=True,
        )
        return {
            "entries": entries,
            "documents": documents,
            "vectorized_documents": vectorized,
            "domains": {row["domain"]: row["count"] for row in rows or []},
        }

    def _count(self, table, where="", params=None):
        row = self._execute(f"SELECT COUNT(*) AS count FROM {table} {where}".strip(), params or (), fetchone=True)
        if not row:
            return 0
        return row.get("count", row.get("COUNT(*)", 0))

    def add_entry(self, name, english="", domain="", category="", shape="", color_scheme=None, tags=None, description=""):
        exists = self._execute(
            f"SELECT COUNT(*) AS count FROM {self._table('text', 'terms')} WHERE `name`=%s",
            (name,),
            fetchone=True,
        )
        count = exists.get("count", exists.get("COUNT(*)", 0)) if exists else 0
        if count:
            return False

        self._execute(
            f"""
            INSERT INTO {self._table('text', 'terms')}
            (`name`, `english`, `domain`, `category`, `shape`, `color_scheme`, `tags`, `description`)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                name,
                english,
                domain,
                category,
                shape,
                json.dumps(color_scheme or [], ensure_ascii=False),
                json.dumps(tags or [], ensure_ascii=False),
                description,
            ),
        )
        return True

    def update_entry(self, eid, **kwargs):
        allowed = {"name", "english", "domain", "category", "shape", "color_scheme", "tags", "description"}
        fields, values = [], []
        for key, value in kwargs.items():
            if key not in allowed:
                continue
            if key in {"color_scheme", "tags"} and isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            fields.append(f"{_quote_identifier(key)}=%s")
            values.append(value)
        if not fields:
            return
        values.append(eid)
        self._execute(
            f"UPDATE {self._table('text', 'terms')} SET {', '.join(fields)} WHERE `id`=%s",
            tuple(values),
        )

    def delete_entry(self, eid):
        self._execute(f"DELETE FROM {self._table('text', 'terms')} WHERE `id`=%s", (eid,))

    def list_entries(self, domain="", search="", limit=100, offset=0):
        where, params = [], []
        if domain:
            where.append("`domain`=%s")
            params.append(domain)
        if search:
            where.append("(`name` LIKE %s OR `english` LIKE %s OR JSON_SEARCH(`tags`, 'one', %s) IS NOT NULL)")
            like = f"%{search}%"
            params.extend([like, like, like])
        clause = "WHERE " + " AND ".join(where) if where else ""
        rows = self._execute(
            f"SELECT * FROM {self._table('text', 'terms')} {clause} ORDER BY `updated_at` DESC LIMIT %s OFFSET %s",
            tuple(params + [limit, offset]),
            fetchall=True,
        )
        total = self._count(self._table("text", "terms"), clause, tuple(params))
        return rows or [], total

    def add_document(self, filename, filepath, file_type="", content=""):
        return self.save_document(filename, filepath, file_type=file_type, content=content, vectorized=0)

    def get_document_by_filepath(self, filepath):
        return self._execute(
            f"SELECT * FROM {self._table('text', 'documents')} WHERE `filepath`=%s",
            (filepath,),
            fetchone=True,
        )

    def save_document(self, filename, filepath, file_type="", content="", vectorized=0):
        existing = self.get_document_by_filepath(filepath)
        if existing:
            self._execute(
                f"""
                UPDATE {self._table('text', 'documents')}
                SET `filename`=%s, `file_type`=%s, `content`=%s, `vectorized`=%s
                WHERE `id`=%s
                """,
                (filename, file_type, content, vectorized, existing["id"]),
            )
            return existing["id"]

        return self._execute(
            f"""
            INSERT INTO {self._table('text', 'documents')}
            (`filename`, `filepath`, `file_type`, `content`, `vectorized`)
            VALUES (%s,%s,%s,%s,%s)
            """,
            (filename, filepath, file_type, content, vectorized),
        )

    def update_document_vector(self, did, content, vectorized=1):
        self._execute(
            f"UPDATE {self._table('text', 'documents')} SET `content`=%s, `vectorized`=%s WHERE `id`=%s",
            (content, vectorized, did),
        )

    def list_documents(self):
        return self._execute(
            f"SELECT * FROM {self._table('text', 'documents')} ORDER BY `created_at` DESC",
            fetchall=True,
        ) or []

    def delete_document(self, did):
        self._execute(f"DELETE FROM {self._table('text', 'documents')} WHERE `id`=%s", (did,))

    def get_setting(self, key, default=""):
        row = self._execute(
            f"SELECT `config_value` FROM {self._table('app', 'model_configs')} WHERE `config_key`=%s",
            (key,),
            fetchone=True,
        )
        return row["config_value"] if row else default

    def set_setting(self, key, value):
        self._execute(
            f"""
            INSERT INTO {self._table('app', 'model_configs')} (`config_key`, `config_value`)
            VALUES (%s,%s)
            ON DUPLICATE KEY UPDATE `config_value`=VALUES(`config_value`)
            """,
            (key, str(value)),
        )

    def list_settings(self, prefix=""):
        if prefix:
            rows = self._execute(
                f"SELECT * FROM {self._table('app', 'model_configs')} WHERE `config_key` LIKE %s ORDER BY `config_key`",
                (prefix + "%",),
                fetchall=True,
            )
        else:
            rows = self._execute(
                f"SELECT * FROM {self._table('app', 'model_configs')} ORDER BY `config_key`",
                fetchall=True,
            )
        return {row["config_key"]: row["config_value"] for row in rows or []}


def _quote_identifier(value):
    cleaned = str(value).replace("`", "``")
    return f"`{cleaned}`"


def build_repository(kind=None, db_path=None, connector=None):
    repository_kind = (kind or os.environ.get("SCI_REPOSITORY_KIND", "sqlite")).strip().lower()
    if repository_kind == "sqlite":
        return SQLiteKnowledgeRepository(db_path=db_path)
    if repository_kind == "mysql":
        return MySQLKnowledgeRepository(connector=connector)
    raise ValueError(f"Unsupported repository kind: {repository_kind}")
