import argparse
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM_DIR = os.path.join(ROOT, "sci-illust-system")
if SYSTEM_DIR not in sys.path:
    sys.path.insert(0, SYSTEM_DIR)

from text_kb.graphrag_manager import GraphRAGTextKBManager


def main():
    parser = argparse.ArgumentParser(description="Incrementally import text corpus and optionally rebuild GraphRAG index.")
    parser.add_argument("--domain", default="biology", help="Focus domain name, default: biology")
    parser.add_argument("--base-dir", default=None, help="Optional text_kb base directory")
    parser.add_argument("--source-dir", default=None, help="Optional external source directory, default: corpus/incoming")
    parser.add_argument("--skip-index", action="store_true", help="Only import documents, do not run graphrag index")
    parser.add_argument("--no-archive", action="store_true", help="Do not move imported incoming files into corpus/archive")
    parser.add_argument("--reset-workspace", action="store_true", help="Clear active raw/cleaned/input/output data before importing")
    args = parser.parse_args()

    manager = GraphRAGTextKBManager(base_dir=args.base_dir, focus_domain=args.domain)
    paths = manager.ensure_workspace(args.domain)

    print(f"[text-kb] domain={paths['domain']}")
    print(f"[text-kb] workspace={paths['domain_root']}")
    print(f"[text-kb] incoming={paths['incoming_root']}")

    if args.reset_workspace:
        reset_result = manager.reset_workspace(args.domain)
        print(f"[reset] success={reset_result['success']} domain={reset_result['domain']}")

    import_result = manager.import_documents(
        domain=args.domain,
        source_dir=args.source_dir,
        archive=not args.no_archive,
    )
    print(
        "[import] imported={imported} skipped_duplicates={skipped_duplicates} "
        "skipped_unsupported={skipped_unsupported} errors={errors}".format(
            imported=import_result["imported"],
            skipped_duplicates=import_result["skipped_duplicates"],
            skipped_unsupported=import_result["skipped_unsupported"],
            errors=len(import_result["errors"]),
        )
    )

    if import_result["errors"]:
        for item in import_result["errors"]:
            print(f"[import][error] {item['filename']}: {item['error']}")

    if args.skip_index:
        status = manager.status(args.domain)
        print(
            f"[status] cleaned={status['cleaned_documents']} input={status['input_documents']} "
            f"index_ready={status['index_ready']}"
        )
        return 0

    index_result = manager.run_index(args.domain)
    print(f"[index] success={index_result.get('success')} returncode={index_result.get('returncode', '-')}")
    if index_result.get("stdout"):
        print(index_result["stdout"])
    if index_result.get("stderr"):
        print(index_result["stderr"])
    return 0 if index_result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
