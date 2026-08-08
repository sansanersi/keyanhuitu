import argparse
import json
import os
import subprocess
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
from web_app.server_data_layer import mysql_schema_statements, mysql_schema_sql


def main():
    parser = argparse.ArgumentParser(description="服务器版 MySQL 联调检查脚本")
    parser.add_argument("--sqlite-db", required=True, help="SQLite knowledge.db 路径")
    parser.add_argument("--schema-output", default=os.path.join(ROOT, "build", "mysql_schema.sql"))
    parser.add_argument("--offline", action="store_true", help="只生成 schema 和迁移 dry-run，不连接 MySQL")
    parser.add_argument("--check-connection", action="store_true", help="检查 MySQL 连接")
    parser.add_argument("--apply-schema", action="store_true", help="在 MySQL 执行 schema")
    parser.add_argument("--apply-migration", action="store_true", help="把 SQLite 数据迁移到 MySQL")
    parser.add_argument("--health-base-url", default="", help="切换 MySQL 后要检查的 Web 地址，例如 http://127.0.0.1:5000")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    if args.offline and (args.check_connection or args.apply_schema or args.apply_migration or args.health_base_url):
        parser.error("--apply-schema cannot be used with --offline; offline mode cannot connect, migrate, or health-check")
    if (args.apply_schema or args.apply_migration) and not args.check_connection:
        parser.error("--apply-schema and --apply-migration require --check-connection")

    source = SQLiteKnowledgeRepository(db_path=os.path.abspath(args.sqlite_db))
    schema_output = os.path.abspath(args.schema_output)
    os.makedirs(os.path.dirname(schema_output), exist_ok=True)
    with open(schema_output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(mysql_schema_sql())

    payload = {
        "mode": "offline" if args.offline else "online",
        "schema": {"generated": True, "path": schema_output},
        "migration_dry_run": {"counts": migration_counts(source)},
        "mysql": {"connection_checked": False, "schema_applied": False, "migration_applied": False},
        "health_check": {"requested": bool(args.health_base_url), "passed": False},
    }

    if args.offline:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return

    target = None
    if args.check_connection:
        target = MySQLKnowledgeRepository()
        _check_mysql_connection(target)
        payload["mysql"]["connection_checked"] = True

    if args.apply_schema:
        target = target or MySQLKnowledgeRepository()
        _apply_schema(target)
        payload["mysql"]["schema_applied"] = True

    if args.apply_migration:
        target = target or MySQLKnowledgeRepository()
        payload["mysql"]["migration_result"] = migrate_knowledge_repository(source, target)
        payload["mysql"]["migration_applied"] = True

    if args.health_base_url:
        _run_health_check(args.health_base_url, args.ollama_url)
        payload["health_check"]["passed"] = True

    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _check_mysql_connection(repository):
    conn = repository._connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 AS ok")
            row = cursor.fetchone()
            if row and row.get("ok", 1) != 1:
                raise RuntimeError("MySQL connection check returned unexpected result")
    finally:
        close = getattr(conn, "close", None)
        if close:
            close()


def _apply_schema(repository):
    conn = repository._connect()
    try:
        with conn.cursor() as cursor:
            for statement in mysql_schema_statements():
                sql = statement.strip()
                if not sql or sql.startswith("--"):
                    continue
                cursor.execute(sql)
        conn.commit()
    finally:
        close = getattr(conn, "close", None)
        if close:
            close()


def _run_health_check(base_url, ollama_url):
    env = os.environ.copy()
    env["SCI_REPOSITORY_KIND"] = "mysql"
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        os.path.join(ROOT, "scripts", "health_check.ps1"),
        "-BaseUrl",
        base_url,
        "-OllamaUrl",
        ollama_url,
    ]
    result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout)


if __name__ == "__main__":
    main()
