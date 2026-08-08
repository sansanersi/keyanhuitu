"""图片库资产存储和图关系边界。"""

import hashlib
import os
import re
from datetime import datetime, timezone


class LocalImageAssetStorage:
    """本地文件资产存储适配器，后续可替换为 MinIO、OSS 或 NAS。"""

    def __init__(self, root_dir):
        self.root_dir = os.path.abspath(root_dir)
        os.makedirs(self.root_dir, exist_ok=True)

    def save_asset(self, filename, content, domain="", category="", metadata=None):
        data = content if isinstance(content, bytes) else str(content).encode("utf-8")
        safe_name = _safe_filename(filename or "asset.bin")
        content_hash = hashlib.sha256(data).hexdigest()
        target_dir = os.path.join(self.root_dir, domain or "general", category or "uncategorized")
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, f"{content_hash[:12]}-{safe_name}")

        with open(target_path, "wb") as handle:
            handle.write(data)

        return {
            "name": os.path.splitext(safe_name)[0],
            "source": "local_files",
            "asset_type": _asset_type_from_filename(safe_name),
            "domain": domain,
            "category": category,
            "file_path": target_path,
            "content_hash": content_hash,
            "size_bytes": len(data),
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def stats(self):
        count = 0
        for _, _, files in os.walk(self.root_dir):
            count += len(files)
        return {"root_dir": self.root_dir, "assets": count, "storage": "local_files"}


class InMemoryImageGraphRepository:
    """图关系 Repository 内存实现，用于本地开发和测试。"""

    def __init__(self):
        self._relations = []

    def add_relation(self, source_asset_id, target_asset_id, relation_type, weight=1.0, metadata=None):
        relation = {
            "source_asset_id": source_asset_id,
            "target_asset_id": target_asset_id,
            "relation_type": relation_type,
            "weight": float(weight),
            "metadata": metadata or {},
        }
        self._relations.append(relation)
        return relation

    def list_relations(self, asset_id=None):
        if not asset_id:
            return list(self._relations)
        return [
            relation
            for relation in self._relations
            if relation["source_asset_id"] == asset_id or relation["target_asset_id"] == asset_id
        ]

    def stats(self):
        return {"relations": len(self._relations)}


def _safe_filename(filename):
    name = os.path.basename(filename).strip() or "asset.bin"
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def _asset_type_from_filename(filename):
    extension = os.path.splitext(filename)[1].lower().lstrip(".")
    if extension in {"svg", "png", "jpg", "jpeg", "webp"}:
        return extension
    return "binary"
