import argparse
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
WEB_APP_DIR = os.path.join(SYSTEM_DIR, "web_app")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)
if WEB_APP_DIR not in sys.path:
    sys.path.insert(0, WEB_APP_DIR)

from web_app.server_data_layer import mysql_schema_sql


def main():
    parser = argparse.ArgumentParser(description="生成服务器版 MySQL 三逻辑库 schema SQL")
    parser.add_argument("--output", required=True, help="输出 SQL 文件路径")
    args = parser.parse_args()

    output_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(mysql_schema_sql())

    print(f"Generated MySQL schema: {output_path}")


if __name__ == "__main__":
    main()
