"""数据访问 Repository 边界。

服务器版 v1 先把服务层和具体数据库实现隔开；当前默认实现仍然复用 SQLite。
"""

import os
from typing import Protocol

try:
    from .database import KnowledgeDatabase
except ImportError:
    from database import KnowledgeDatabase


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


def build_repository(kind=None, db_path=None):
    repository_kind = (kind or os.environ.get("SCI_REPOSITORY_KIND", "sqlite")).strip().lower()
    if repository_kind != "sqlite":
        raise ValueError(f"Unsupported repository kind: {repository_kind}")
    return SQLiteKnowledgeRepository(db_path=db_path)
