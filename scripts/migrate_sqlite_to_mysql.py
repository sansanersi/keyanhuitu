import argparse
import json
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

from web_app.migrations import migrate_knowledge_repository, migration_counts
from web_app.repositories import MySQLKnowledgeRepository, SQLiteKnowledgeRepository


def main():
    parser = argparse.ArgumentParser(description="从 SQLite 运行库迁移到服务器版 MySQL 三逻辑库")
    parser.add_argument("--sqlite-db", required=True, help="SQLite knowledge.db 路径")
    parser.add_argument("--dry-run", action="store_true", help="只统计源数据，不写入 MySQL")
    parser.add_argument("--apply", action="store_true", help="执行写入 MySQL")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        parser.error("--dry-run 和 --apply 不能同时使用")
    if not args.dry_run and not args.apply:
        args.dry_run = True

    source = SQLiteKnowledgeRepository(db_path=os.path.abspath(args.sqlite_db))

    if args.dry_run:
        payload = {"mode": "dry-run", "counts": migration_counts(source)}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return

    target = MySQLKnowledgeRepository()
    payload = {"mode": "apply", "migrated": migrate_knowledge_repository(source, target)}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
