"""从清洗产物导入文本库和图片库。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_DIR = ROOT / "sci-illust-system"
WEB_APP_DIR = SYSTEM_DIR / "web_app"

DOMAIN_EN_FALLBACK = {
    "生物学": "biology",
    "化学": "chemistry",
    "环境科学": "environmental_science",
    "材料科学": "materials_science",
}

CATEGORY_EN_FALLBACK = {
    "结构生物学": "structural_biology",
    "官能团": "functional_groups",
    "细胞分裂": "cell_division",
    "生态系统组件": "ecosystem_components",
    "免疫学组件": "immunology_components",
    "细胞器": "organelles",
    "晶体结构": "crystal_structures",
    "循环": "cycles",
    "亚细胞结构": "subcellular_structures",
    "遗传学组件": "genetic_components",
    "组织结构": "tissue_structures",
    "生化分子": "biomolecules",
    "代谢过程": "metabolic_processes",
    "纳米材料": "nanomaterials",
    "反应符号": "reaction_symbols",
    "信号通路组件": "signaling_pathway_components",
    "微生物组件": "microbiology_components",
}


def _load_repository_modules():
    import sys

    for path in (str(SYSTEM_DIR), str(WEB_APP_DIR)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from web_app.repositories import build_repository

    return build_repository


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从清洗产物导入文本库和图片库")
    parser.add_argument("cleaned_root", help="data_2_cleaned 根目录")
    parser.add_argument("--target", choices=("text_kb", "image_kb", "both"), default="both")
    parser.add_argument("--repository-kind", default="", help="默认读取 SCI_REPOSITORY_KIND")
    parser.add_argument("--db-path", default="", help="SQLite DB 路径")
    return parser.parse_args(argv)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_cleaned_bundle(cleaned_root: Path) -> dict:
    cleaned_root = Path(cleaned_root)
    elements_path = cleaned_root / "elements" / "kb_a_elements.cleaned.json"
    element_index_path = cleaned_root / "elements" / "element_index.cleaned.json"
    literature_path = cleaned_root / "literature" / "normalized.cleaned.jsonl"
    return {
        "image_kb": {
            "elements": load_json(elements_path),
            "element_index": load_json(element_index_path) if element_index_path.exists() else {},
        },
        "text_kb": {"documents": load_jsonl(literature_path)},
    }


def document_identity(document: dict) -> tuple[str, str]:
    doi = str(document.get("doi") or "").strip().lower()
    url = str(document.get("url") or "").strip()
    if doi:
        return ("doi", doi)
    if url:
        return ("url", url)
    return ("record_id", str(document.get("record_id") or document.get("title") or "").strip())


def build_document_filepath(document: dict) -> str:
    identity_kind, identity_value = document_identity(document)
    base = identity_value or str(document.get("title") or document.get("record_id") or "unknown")
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_", ".") else "_" for ch in base)[:120].strip("._") or "unknown"
    filename = f"{safe}.txt"
    return str((WEB_APP_DIR / "data" / "text_kb" / "imported_cleaned" / identity_kind / filename).resolve())


def build_document_content(document: dict) -> str:
    parts = []
    if document.get("title"):
        parts.append(f"标题: {document['title']}")
    if document.get("doi"):
        parts.append(f"DOI: {document['doi']}")
    if document.get("url"):
        parts.append(f"URL: {document['url']}")
    if document.get("year") is not None:
        parts.append(f"年份: {document['year']}")
    if document.get("journal"):
        parts.append(f"期刊: {document['journal']}")
    if document.get("authors"):
        parts.append("作者: " + "；".join(document["authors"]))
    if document.get("keywords"):
        parts.append("关键词: " + "；".join(document["keywords"]))
    parts.append("")
    parts.append(document.get("content", ""))
    return "\n".join(parts).strip()


def build_taxonomy_stats(elements: list[dict], field_name: str) -> list[dict]:
    counts = {}
    for element in elements:
        zh = str(element.get(field_name) or "").strip()
        en = str(element.get(f"{field_name}_en") or "").strip()
        if not en:
            fallback = DOMAIN_EN_FALLBACK if field_name == "domain" else CATEGORY_EN_FALLBACK
            en = fallback.get(zh, "")
        key = (zh, en)
        if not zh and not en:
            continue
        counts[key] = counts.get(key, 0) + 1
    rows = []
    for (zh, en), count in sorted(counts.items(), key=lambda item: (-item[1], item[0][0], item[0][1])):
        rows.append({f"{field_name}_zh": zh, f"{field_name}_en": en, "count": count})
    return rows


def import_text_kb(repository, documents: list[dict]) -> dict:
    imported = 0
    skipped = 0
    for document in documents:
        filepath = build_document_filepath(document)
        if repository.get_document_by_filepath(filepath):
            skipped += 1
            continue
        repository.save_document(
            filename=Path(filepath).name,
            filepath=filepath,
            file_type="txt",
            content=build_document_content(document),
            vectorized=0,
        )
        imported += 1
    repository.set_setting("text_kb_import_last_count", imported)
    return {"documents_imported": imported, "documents_skipped": skipped, "documents_total": len(documents)}


def import_image_kb(repository, elements: list[dict]) -> dict:
    imported = 0
    skipped = 0
    for element in elements:
        created = repository.add_entry(
            name=str(element.get("name") or "").strip(),
            english=str(element.get("english") or "").strip(),
            domain=str(element.get("domain") or "").strip(),
            category=str(element.get("category") or "").strip(),
            shape=str(element.get("shape") or "").strip(),
            color_scheme=element.get("color_scheme") or [],
            tags=element.get("tags") or [],
            description=str(element.get("description") or "").strip(),
        )
        if created:
            imported += 1
        else:
            skipped += 1
    repository.set_setting("image_kb_import_last_count", imported)
    return {
        "entries_imported": imported,
        "entries_skipped": skipped,
        "entries_total": len(elements),
        "domain_counts": build_taxonomy_stats(elements, "domain"),
        "category_counts": build_taxonomy_stats(elements, "category"),
    }


def run_import(cleaned_root: Path, target: str = "both", repository_kind: str = "", db_path: Path | str = "") -> dict:
    payload = load_cleaned_bundle(cleaned_root)
    build_repository = _load_repository_modules()
    repository = build_repository(kind=repository_kind or None, db_path=str(db_path) if db_path else None)

    text_result = {"documents_imported": 0, "documents_skipped": 0, "documents_total": 0}
    image_result = {"entries_imported": 0, "entries_skipped": 0, "entries_total": 0}

    if target in {"text_kb", "both"}:
        text_result = import_text_kb(repository, payload["text_kb"]["documents"])
    if target in {"image_kb", "both"}:
        image_result = import_image_kb(repository, payload["image_kb"]["elements"])

    import_report = {
        "target": target,
        "text_kb": text_result,
        "image_kb": image_result,
        "repository_stats": repository.stats,
    }
    report_path = Path(cleaned_root).parent / "import_reports"
    report_path.mkdir(parents=True, exist_ok=True)
    (report_path / f"{target}.json").write_text(json.dumps(import_report, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "target": target,
        "cleaned_root": str(Path(cleaned_root).resolve()),
        "repository_kind": (repository_kind or os.environ.get("SCI_REPOSITORY_KIND", "sqlite")).strip().lower() or "sqlite",
        "text_kb": text_result,
        "image_kb": image_result,
        "repository_stats": repository.stats,
        "report_path": str((report_path / f"{target}.json").resolve()),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_import(
        Path(args.cleaned_root),
        target=args.target,
        repository_kind=args.repository_kind,
        db_path=args.db_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
