"""数据迁移工具函数。"""


def migration_counts(source_repository):
    entries, total_entries = source_repository.list_entries(limit=100000, offset=0)
    documents = source_repository.list_documents()
    settings = source_repository.list_settings()
    return {
        "entries": total_entries if total_entries is not None else len(entries),
        "documents": len(documents),
        "settings": len(settings),
    }


def migrate_knowledge_repository(source_repository, target_repository):
    entries, _ = source_repository.list_entries(limit=100000, offset=0)
    documents = source_repository.list_documents()
    settings = source_repository.list_settings()

    migrated = {"entries": 0, "documents": 0, "settings": 0}
    for entry in entries:
        target_repository.add_entry(
            name=entry.get("name", ""),
            english=entry.get("english", ""),
            domain=entry.get("domain", ""),
            category=entry.get("category", ""),
            shape=entry.get("shape", ""),
            color_scheme=_jsonish(entry.get("color_scheme"), []),
            tags=_jsonish(entry.get("tags"), []),
            description=entry.get("description", ""),
        )
        migrated["entries"] += 1

    for document in documents:
        target_repository.save_document(
            filename=document.get("filename", ""),
            filepath=document.get("filepath", ""),
            file_type=document.get("file_type", ""),
            content=document.get("content", ""),
            vectorized=document.get("vectorized", 0),
        )
        migrated["documents"] += 1

    for key, value in settings.items():
        target_repository.set_setting(key, value)
        migrated["settings"] += 1

    return migrated


def _jsonish(value, default):
    if value in (None, ""):
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        import json

        return json.loads(value)
    except Exception:
        return default
