"""清洗 data_2 科研绘图知识包。"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


ALLOWED_RELATIONS = {
    "related_to",
    "regulates",
    "activates",
    "inhibits",
    "binds_to",
    "phosphorylates",
    "produces",
    "composed_of",
    "located_in",
}

NOISE_TOKENS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "div",
    "span",
    "br",
    "p",
    "unknown",
}

DOMAIN_MAP = {
    "����ѧ": ("生物学", "biology"),
    "生物学": ("生物学", "biology"),
    "��ѧ": ("化学", "chemistry"),
    "化学": ("化学", "chemistry"),
    "������ѧ": ("环境科学", "environmental_science"),
    "环境科学": ("环境科学", "environmental_science"),
    "���Ͽ�ѧ": ("材料科学", "materials_science"),
    "材料科学": ("材料科学", "materials_science"),
}

CATEGORY_MAP = {
    "�ṹ����ѧ": ("结构生物学", "structural_biology"),
    "结构生物学": ("结构生物学", "structural_biology"),
    "������": ("官能团", "functional_groups"),
    "官能团": ("官能团", "functional_groups"),
    "ϸ������": ("细胞分裂", "cell_division"),
    "细胞分裂": ("细胞分裂", "cell_division"),
    "��̬ϵͳ���": ("生态系统组件", "ecosystem_components"),
    "生态系统组件": ("生态系统组件", "ecosystem_components"),
    "����ѧ���": ("免疫学组件", "immunology_components"),
    "免疫学组件": ("免疫学组件", "immunology_components"),
    "ϸ����": ("细胞器", "organelles"),
    "细胞器": ("细胞器", "organelles"),
    "����ṹ": ("晶体结构", "crystal_structures"),
    "晶体结构": ("晶体结构", "crystal_structures"),
    "ѭ��": ("循环", "cycles"),
    "循环": ("循环", "cycles"),
    "��ϸ���ṹ": ("亚细胞结构", "subcellular_structures"),
    "亚细胞结构": ("亚细胞结构", "subcellular_structures"),
    "�Ŵ�ѧ���": ("遗传学组件", "genetic_components"),
    "遗传学组件": ("遗传学组件", "genetic_components"),
    "��֯�ṹ": ("组织结构", "tissue_structures"),
    "组织结构": ("组织结构", "tissue_structures"),
    "�������": ("生化分子", "biomolecules"),
    "生化分子": ("生化分子", "biomolecules"),
    "��������": ("代谢过程", "metabolic_processes"),
    "代谢过程": ("代谢过程", "metabolic_processes"),
    "���ײ���": ("纳米材料", "nanomaterials"),
    "纳米材料": ("纳米材料", "nanomaterials"),
    "��Ӧ����": ("反应符号", "reaction_symbols"),
    "反应符号": ("反应符号", "reaction_symbols"),
    "�ź�ͨ·���": ("信号通路组件", "signaling_pathway_components"),
    "信号通路组件": ("信号通路组件", "signaling_pathway_components"),
    "΢�������": ("微生物组件", "microbiology_components"),
    "微生物组件": ("微生物组件", "microbiology_components"),
}

COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
DOI_PATTERN = re.compile(r"^10\.\S+/\S+$")
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]")
WHITESPACE_PATTERN = re.compile(r"\s+")
HTML_PATTERN = re.compile(r"<[^>]+>")
BAD_FILENAME_PATTERN = re.compile(r'[\\/:*?"<>|]+')
MOJIBAKE_PATTERN = re.compile(r"[�]|[ÂÃÐÑØÆ]|[\u0370-\u03ff]{2,}|[ϸ��]")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清洗 data_2 数据包")
    parser.add_argument("zip_path", help="data_2 zip 路径")
    parser.add_argument("--output-root", default="build", help="输出根目录")
    parser.add_argument("--min-relation-confidence", type=float, default=0.8, help="关系最小置信度")
    parser.add_argument("--overwrite", action="store_true", help="覆盖输出目录")
    parser.add_argument("--sample-limit", type=int, default=20, help="验证抽样上限")
    return parser.parse_args(argv)


def prepare_output_dirs(output_root: Path, overwrite: bool) -> dict[str, Path]:
    output_root = Path(output_root)
    if overwrite and output_root.exists():
        shutil.rmtree(output_root)

    cleaned_root = output_root / "data_2_cleaned"
    reports_root = output_root / "data_2_reports"
    paths = {
        "output_root": output_root,
        "cleaned_root": cleaned_root,
        "reports_root": reports_root,
        "elements_root": cleaned_root / "elements",
        "literature_root": cleaned_root / "literature",
        "literature_text_root": cleaned_root / "literature" / "texts",
        "mappings_root": cleaned_root / "mappings",
        "kg_root": cleaned_root / "kg",
    }
    for path in paths.values():
        if path == output_root:
            continue
        path.mkdir(parents=True, exist_ok=True)
    return paths


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_whitespace(value: object) -> str:
    text = CONTROL_PATTERN.sub(" ", str(value or ""))
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def strip_html_to_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = HTML_PATTERN.sub(" ", text)
    return normalize_whitespace(text)


def sanitize_filename(value: object, fallback: str, max_length: int = 120) -> str:
    cleaned = html.unescape(normalize_whitespace(value))
    cleaned = BAD_FILENAME_PATTERN.sub("_", cleaned)
    cleaned = cleaned.strip(". ")
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip(" ._")
    return cleaned or fallback


def normalize_doi(value: object) -> str:
    raw = normalize_whitespace(value).lower()
    raw = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw)
    return raw if DOI_PATTERN.match(raw) else ""


def normalize_url(value: object) -> str:
    raw = normalize_whitespace(value)
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return parsed.geturl()


def normalize_list(values: object) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    result = []
    seen = set()
    for item in values:
        cleaned = normalize_whitespace(item)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def normalize_element_key(value: object) -> str:
    key = normalize_whitespace(value).lower()
    key = re.sub(r"\s+", "_", key)
    key = re.sub(r"[^0-9a-zA-Z_\-\u4e00-\u9fff]+", "_", key)
    return key.strip("_")


def normalize_label_pair(value: object, mapping: dict[str, tuple[str, str]]) -> tuple[str, str]:
    raw = normalize_whitespace(value)
    if not raw:
        return ("", "")
    if raw in mapping:
        return mapping[raw]
    return (raw, normalize_element_key(raw))


def is_probable_noise_text(value: object) -> bool:
    text = normalize_whitespace(value)
    if not text:
        return True
    lower = text.lower()
    if lower in NOISE_TOKENS:
        return True
    if MOJIBAKE_PATTERN.search(text):
        return True
    if len(text) == 1 and not re.search(r"[\u4e00-\u9fffA-Za-z0-9]", text):
        return True
    return False


def is_broken_relation_fragment(value: object) -> bool:
    text = normalize_whitespace(value)
    if not text:
        return True
    if is_probable_noise_text(text):
        return True
    if len(text) <= 1:
        return True
    if text.startswith(("，", ",", "。", ".", "的", "而", "并")):
        return True
    if text.endswith(("，", ",", "。", ".", "的", "而", "并", "后")):
        return True
    return False


def append_exception(
    exceptions: list[dict],
    *,
    stage: str,
    source_file: str,
    record_id: str,
    field: str,
    issue_type: str,
    severity: str,
    original_value: object,
    action: str,
    message: str,
) -> None:
    exceptions.append(
        {
            "stage": stage,
            "source_file": source_file,
            "record_id": str(record_id),
            "field": field,
            "issue_type": issue_type,
            "severity": severity,
            "original_value": original_value,
            "action": action,
            "message": message,
        }
    )


def unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def filter_color_scheme(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str) and COLOR_PATTERN.match(value)]


def make_element_key(element: dict) -> str:
    for candidate in (element.get("element_id"), element.get("english"), element.get("name")):
        key = normalize_element_key(candidate)
        if key:
            return key
    return ""


def clean_element_record(element: dict, source_file: str, exceptions: list[dict]) -> dict | None:
    element_id = make_element_key(element)
    name = normalize_whitespace(element.get("name"))
    english = normalize_whitespace(element.get("english"))
    if not name and not english:
        append_exception(
            exceptions,
            stage="elements",
            source_file=source_file,
            record_id=element_id or "unknown",
            field="name",
            issue_type="missing_required_field",
            severity="warning",
            original_value={"name": element.get("name"), "english": element.get("english")},
            action="drop_record",
            message="元素记录缺少 name 和 english。",
        )
        return None
    if not element_id:
        append_exception(
            exceptions,
            stage="elements",
            source_file=source_file,
            record_id="unknown",
            field="element_id",
            issue_type="missing_required_field",
            severity="warning",
            original_value=element,
            action="drop_record",
            message="元素记录无法生成稳定 element_id。",
        )
        return None
    if (name and is_probable_noise_text(name)) and (not english or is_probable_noise_text(english)):
        append_exception(
            exceptions,
            stage="elements",
            source_file=source_file,
            record_id=element_id,
            field="name",
            issue_type="invalid_encoding",
            severity="warning",
            original_value={"name": name, "english": english},
            action="drop_record",
            message="元素主名称疑似乱码或无语义。",
        )
        return None

    domain_cn, domain_en = normalize_label_pair(element.get("domain"), DOMAIN_MAP)
    category_cn, category_en = normalize_label_pair(element.get("category"), CATEGORY_MAP)

    return {
        "element_id": element_id,
        "name": name,
        "english": english,
        "domain": domain_cn,
        "domain_en": domain_en,
        "category": category_cn,
        "category_en": category_en,
        "shape": normalize_whitespace(element.get("shape")),
        "tags": unique_sorted(normalize_list(element.get("tags"))),
        "color_scheme": filter_color_scheme(element.get("color_scheme")),
        "description": normalize_whitespace(element.get("description")),
        "source_count": 1,
    }


def merge_element_records(current: dict, incoming: dict) -> dict:
    merged = dict(current)
    for field in ("name", "english", "domain", "domain_en", "category", "category_en", "shape", "description"):
        if not merged.get(field) and incoming.get(field):
            merged[field] = incoming[field]
    merged["tags"] = unique_sorted(list(merged.get("tags", [])) + list(incoming.get("tags", [])))
    merged["color_scheme"] = unique_sorted(list(merged.get("color_scheme", [])) + list(incoming.get("color_scheme", [])))
    merged["source_count"] = int(merged.get("source_count", 1)) + int(incoming.get("source_count", 1))
    return merged


def extract_domain_vocab_elements(domain_vocab: dict) -> list[dict]:
    extracted = []
    for domain_key, domain in (domain_vocab.get("domains") or {}).items():
        domain_name = normalize_whitespace(domain.get("name") or domain_key)
        for category_key, category in (domain.get("element_categories") or {}).items():
            category_name = normalize_whitespace(category.get("name") or category_key)
            for element in category.get("elements", []):
                row = dict(element)
                row.setdefault("domain", domain_name)
                row.setdefault("category", category_name)
                extracted.append(row)
    return extracted


def clean_elements(domain_vocab: dict, kb_elements: list[dict], exceptions: list[dict]) -> dict:
    index: dict[str, dict] = {}
    cleaned_rows = []
    domain_rows = extract_domain_vocab_elements(domain_vocab)
    for source_file, rows in (
        ("data_2/data/domain_vocab.json", domain_rows),
        ("data_2/data/kb_exports/kb_a_elements.json", kb_elements),
    ):
        for row in rows:
            cleaned = clean_element_record(row, source_file, exceptions)
            if not cleaned:
                continue
            key = cleaned["element_id"]
            if key in index:
                append_exception(
                    exceptions,
                    stage="elements",
                    source_file=source_file,
                    record_id=key,
                    field="element_id",
                    issue_type="duplicate_merged",
                    severity="info",
                    original_value=row,
                    action="merge_record",
                    message="重复元素已合并。",
                )
                index[key] = merge_element_records(index[key], cleaned)
            else:
                index[key] = cleaned
    for key in sorted(index):
        cleaned_rows.append(index[key])

    cleaned_domain_vocab = {
        "metadata": domain_vocab.get("metadata", {}),
        "domains": domain_vocab.get("domains", {}),
        "figure_types": domain_vocab.get("figure_types", []),
        "view_types": domain_vocab.get("view_types", []),
        "spatial_relations": domain_vocab.get("spatial_relations", []),
        "style_references": domain_vocab.get("style_references", []),
    }
    return {
        "domain_vocab": cleaned_domain_vocab,
        "kb_a_elements": cleaned_rows,
        "element_index": index,
        "counts": {
            "domain_vocab_elements_raw": len(domain_rows),
            "kb_elements_raw": len(kb_elements),
            "elements_cleaned": len(cleaned_rows),
        },
    }


def safe_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def make_literature_key(record: dict) -> str:
    for candidate in (
        record.get("doi"),
        record.get("url"),
        f"{record.get('source')}::{record.get('record_id') or record.get('id')}".strip(":"),
        record.get("title"),
    ):
        key = normalize_whitespace(candidate).lower()
        if key:
            return key
    return ""


def clean_literature_record(record: dict, source_file: str, record_id: str, exceptions: list[dict]) -> dict | None:
    title = normalize_whitespace(record.get("title"))
    raw_content = record.get("content") or record.get("abstract") or ""
    cleaned_content = strip_html_to_text(raw_content)
    if raw_content and cleaned_content != normalize_whitespace(raw_content):
        append_exception(
            exceptions,
            stage="literature",
            source_file=source_file,
            record_id=record_id,
            field="content",
            issue_type="html_removed",
            severity="info",
            original_value=str(raw_content)[:200],
            action="strip_html",
            message="正文中检测到 HTML 标签，已转为纯文本。",
        )
    doi = normalize_doi(record.get("doi"))
    url = normalize_url(record.get("url"))
    year = safe_int(record.get("year"))
    if record.get("year") not in (None, "") and year is None:
        append_exception(
            exceptions,
            stage="literature",
            source_file=source_file,
            record_id=record_id,
            field="year",
            issue_type="missing_required_field",
            severity="info",
            original_value=record.get("year"),
            action="set_null",
            message="年份无法解析，已置空。",
        )
    if record.get("doi") and not doi:
        append_exception(
            exceptions,
            stage="literature",
            source_file=source_file,
            record_id=record_id,
            field="doi",
            issue_type="invalid_doi",
            severity="info",
            original_value=record.get("doi"),
            action="clear_field",
            message="DOI 不合法，已清空。",
        )
    if record.get("url") and not url:
        append_exception(
            exceptions,
            stage="literature",
            source_file=source_file,
            record_id=record_id,
            field="url",
            issue_type="invalid_url",
            severity="info",
            original_value=record.get("url"),
            action="clear_field",
            message="URL 不合法，已清空。",
        )
    if not cleaned_content:
        append_exception(
            exceptions,
            stage="literature",
            source_file=source_file,
            record_id=record_id,
            field="content",
            issue_type="empty_content_after_cleaning",
            severity="warning",
            original_value=raw_content,
            action="drop_record",
            message="正文清洗后为空。",
        )
        return None
    if not title and not doi and not url and not normalize_whitespace(record_id):
        append_exception(
            exceptions,
            stage="literature",
            source_file=source_file,
            record_id=record_id,
            field="title",
            issue_type="missing_required_field",
            severity="warning",
            original_value=record,
            action="drop_record",
            message="文献记录缺少稳定标识。",
        )
        return None
    return {
        "record_id": normalize_whitespace(record_id),
        "source": normalize_whitespace(record.get("source")),
        "title": title,
        "content": cleaned_content,
        "doi": doi,
        "url": url,
        "year": year,
        "type": normalize_whitespace(record.get("type")),
        "fetched_at": normalize_whitespace(record.get("fetched_at")),
        "authors": normalize_list(record.get("authors")),
        "keywords": normalize_list(record.get("keywords")),
        "journal": normalize_whitespace(record.get("journal")),
        "matched_terms": normalize_list(record.get("matched_terms")),
        "conclusion": strip_html_to_text(record.get("conclusion")),
    }


def literature_score(record: dict) -> tuple[int, int, int]:
    metadata_score = sum(1 for field in ("doi", "url", "journal") if record.get(field))
    return (len(record.get("content", "")), metadata_score, len(record.get("authors", [])) + len(record.get("keywords", [])))


def merge_literature_records(current: dict, incoming: dict) -> dict:
    keep, other = (incoming, current) if literature_score(incoming) > literature_score(current) else (current, incoming)
    merged = dict(keep)
    for field in ("record_id", "source", "title", "content", "doi", "url", "year", "type", "fetched_at", "journal", "conclusion"):
        if not merged.get(field) and other.get(field):
            merged[field] = other[field]
    merged["authors"] = unique_sorted(list(merged.get("authors", [])) + list(other.get("authors", [])))
    merged["keywords"] = unique_sorted(list(merged.get("keywords", [])) + list(other.get("keywords", [])))
    merged["matched_terms"] = unique_sorted(list(merged.get("matched_terms", [])) + list(other.get("matched_terms", [])))
    return merged


def clean_literature(normalized_docs: list[dict], exported_docs: list[dict], exceptions: list[dict]) -> dict:
    key_index: dict[str, dict] = {}
    cleaned_rows = []
    source_map = [
        ("normalized", "data_2/data/normalized", normalized_docs),
        ("exported", "data_2/data/kb_exports/kb_b_literature.jsonl", exported_docs),
    ]
    for source_kind, source_file, rows in source_map:
        for row in rows:
            record_id = normalize_whitespace(row.get("id") or row.get("record_id") or row.get("doi") or row.get("title"))
            cleaned = clean_literature_record(row, source_file, record_id, exceptions)
            if not cleaned:
                continue
            cleaned["source_kind"] = source_kind
            key = make_literature_key(cleaned)
            if key in key_index:
                append_exception(
                    exceptions,
                    stage="literature",
                    source_file=source_file,
                    record_id=record_id,
                    field="dedupe_key",
                    issue_type="duplicate_merged",
                    severity="info",
                    original_value=row,
                    action="merge_record",
                    message="重复文献已合并。",
                )
                key_index[key] = merge_literature_records(key_index[key], cleaned)
            else:
                key_index[key] = cleaned
    literature_index = {}
    for key in sorted(key_index):
        item = key_index[key]
        cleaned_rows.append(item)
        if item.get("doi"):
            literature_index[item["doi"]] = item
        if item.get("url"):
            literature_index[item["url"]] = item
        if item.get("record_id"):
            literature_index[f"id::{item['record_id']}"] = item
        if item.get("title"):
            literature_index[f"title::{item['title'].lower()}"] = item
    return {
        "normalized": cleaned_rows,
        "kb_b_literature": cleaned_rows,
        "literature_index": literature_index,
        "counts": {
            "normalized_raw": len(normalized_docs),
            "literature_export_raw": len(exported_docs),
            "literature_cleaned": len(cleaned_rows),
        },
    }


def normalize_reference_link(value: object) -> tuple[str, str]:
    doi = normalize_doi(value)
    if doi:
        return ("doi", doi)
    url = normalize_url(value)
    if url:
        return ("url", url)
    return ("", "")


def clean_element_literature_map(raw_map: dict, element_index: dict, literature_index: dict, exceptions: list[dict]) -> dict:
    cleaned_linkage = {}
    for element_id, refs in (raw_map.get("linkage") or {}).items():
        if element_id not in element_index:
            append_exception(
                exceptions,
                stage="mappings",
                source_file="data_2/data/kb_exports/element_literature_map.json",
                record_id=element_id,
                field="element_id",
                issue_type="unknown_element_reference",
                severity="warning",
                original_value=refs,
                action="drop_mapping",
                message="映射指向不存在的元素。",
            )
            continue
        kept = []
        for ref in refs:
            _, normalized = normalize_reference_link(ref)
            if not normalized:
                append_exception(
                    exceptions,
                    stage="mappings",
                    source_file="data_2/data/kb_exports/element_literature_map.json",
                    record_id=element_id,
                    field="reference",
                    issue_type="invalid_doi" if "10." in str(ref) else "invalid_url",
                    severity="info",
                    original_value=ref,
                    action="drop_reference",
                    message="映射中的文献引用不合法。",
                )
                continue
            if normalized not in literature_index:
                append_exception(
                    exceptions,
                    stage="mappings",
                    source_file="data_2/data/kb_exports/element_literature_map.json",
                    record_id=element_id,
                    field="reference",
                    issue_type="unmatched_literature_reference",
                    severity="warning",
                    original_value=ref,
                    action="drop_reference",
                    message="映射引用未命中清洗后的文献索引。",
                )
                continue
            kept.append(normalized)
        if kept:
            cleaned_linkage[element_id] = sorted(set(kept))
    return {
        "generated_at": raw_map.get("generated_at"),
        "description": raw_map.get("description", ""),
        "element_count": len(cleaned_linkage),
        "literature_count": len({ref for refs in cleaned_linkage.values() for ref in refs}),
        "linked_elements": len(cleaned_linkage),
        "total_links": sum(len(refs) for refs in cleaned_linkage.values()),
        "linkage": cleaned_linkage,
    }


def clean_entity_record(record: dict, exceptions: list[dict]) -> dict | None:
    name = normalize_whitespace(record.get("name"))
    if not name or is_probable_noise_text(name):
        append_exception(
            exceptions,
            stage="kg",
            source_file="data_2/data/kg_output/entities.json",
            record_id=normalize_whitespace(record.get("id")) or name or "unknown",
            field="name",
            issue_type="noise_entity_filtered",
            severity="info",
            original_value=name,
            action="drop_entity",
            message="图谱实体疑似噪声，已过滤。",
        )
        return None
    aliases = [alias for alias in normalize_list(record.get("aliases")) if not is_probable_noise_text(alias)]
    return {
        "id": record.get("id"),
        "name": name,
        "type": normalize_whitespace(record.get("type")),
        "aliases": sorted(set(aliases)),
        "frequency": safe_int(record.get("frequency")) or 0,
        "confidence": float(record.get("confidence") or 0),
        "created_at": normalize_whitespace(record.get("created_at")),
    }


def clean_relation_record(record: dict, min_confidence: float, exceptions: list[dict]) -> dict | None:
    subject = normalize_whitespace(record.get("subject"))
    relation = normalize_whitespace(record.get("relation")).lower()
    obj = normalize_whitespace(record.get("object"))
    confidence = float(record.get("confidence") or 0)
    if confidence < min_confidence:
        append_exception(
            exceptions,
            stage="kg",
            source_file="data_2/data/kg_output/relations.json",
            record_id=f"{subject}->{obj}",
            field="confidence",
            issue_type="low_confidence_relation_filtered",
            severity="info",
            original_value=confidence,
            action="drop_relation",
            message="关系置信度低于阈值，已过滤。",
        )
        return None
    if is_broken_relation_fragment(subject) or is_broken_relation_fragment(obj):
        append_exception(
            exceptions,
            stage="kg",
            source_file="data_2/data/kg_output/relations.json",
            record_id=f"{subject}->{obj}",
            field="subject_object",
            issue_type="broken_relation_filtered",
            severity="info",
            original_value={"subject": subject, "object": obj},
            action="drop_relation",
            message="关系主语或宾语疑似残句，已过滤。",
        )
        return None
    if not relation:
        relation = "other"
    elif relation not in ALLOWED_RELATIONS:
        relation = "other"
    return {
        "subject": subject,
        "relation": relation,
        "object": obj,
        "confidence": confidence,
        "source_doc": normalize_whitespace(record.get("source_doc")),
        "source_docs": normalize_list(record.get("source_docs")),
        "source_text": strip_html_to_text(record.get("source_text")),
        "source_texts": normalize_list(record.get("source_texts")),
    }


def clean_kg(
    entities_payload: dict,
    relations_payload: list[dict],
    triples_payload: dict,
    element_index: dict,
    exceptions: list[dict],
    min_confidence: float,
) -> dict:
    entities = []
    alias_index = {}
    canonical_names = {}
    for raw_entity in entities_payload.get("entities", []):
        entity = clean_entity_record(raw_entity, exceptions)
        if not entity:
            continue
        entity_key = normalize_element_key(entity["name"])
        if entity_key in element_index:
            entity["canonical_element_id"] = entity_key
        entities.append(entity)
        canonical_names[entity["name"]] = entity["name"]
        for alias in entity.get("aliases", []):
            alias_index[alias] = entity["name"]

    relations = []
    for raw_relation in relations_payload:
        relation = clean_relation_record(raw_relation, min_confidence, exceptions)
        if relation:
            if normalize_element_key(relation["subject"]) in element_index:
                relation["canonical_subject"] = normalize_element_key(relation["subject"])
            if normalize_element_key(relation["object"]) in element_index:
                relation["canonical_object"] = normalize_element_key(relation["object"])
            relations.append(relation)

    triples = []
    for raw_triple in triples_payload.get("triples", []):
        triple = clean_relation_record(raw_triple, min_confidence, exceptions)
        if not triple:
            continue
        triple["id"] = raw_triple.get("id")
        triple["sources"] = normalize_list(raw_triple.get("sources"))
        triple["created_at"] = normalize_whitespace(raw_triple.get("created_at"))
        if normalize_element_key(triple["subject"]) in element_index:
            triple["canonical_subject"] = normalize_element_key(triple["subject"])
        if normalize_element_key(triple["object"]) in element_index:
            triple["canonical_object"] = normalize_element_key(triple["object"])
        triples.append(triple)

    return {
        "entities": {"metadata": {"total": len(entities)}, "entities": entities},
        "relations": relations,
        "triples": {"metadata": {"total": len(triples)}, "triples": triples},
        "alias_index": alias_index,
        "counts": {
            "entities_raw": len(entities_payload.get("entities", [])),
            "entities_cleaned": len(entities),
            "relations_raw": len(relations_payload),
            "relations_cleaned": len(relations),
            "triples_raw": len(triples_payload.get("triples", [])),
            "triples_cleaned": len(triples),
        },
    }


def load_json_from_zip(zf: zipfile.ZipFile, member: str):
    return json.loads(zf.read(member).decode("utf-8"))


def load_jsonl_from_zip(zf: zipfile.ZipFile, member: str) -> list[dict]:
    rows = []
    text = zf.read(member).decode("utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_normalized_documents(zf: zipfile.ZipFile) -> list[dict]:
    docs = []
    for member in sorted(zf.namelist()):
        if member.startswith("data_2/data/normalized/") and member.endswith(".json"):
            row = load_json_from_zip(zf, member)
            row["_source_file"] = member
            docs.append(row)
    return docs


def write_cleaned_outputs(paths: dict[str, Path], elements: dict, literature: dict, mapping: dict, kg: dict) -> None:
    write_json(paths["elements_root"] / "domain_vocab.cleaned.json", elements["domain_vocab"])
    write_json(paths["elements_root"] / "kb_a_elements.cleaned.json", elements["kb_a_elements"])
    write_json(paths["elements_root"] / "element_index.cleaned.json", elements["element_index"])

    write_jsonl(paths["literature_root"] / "normalized.cleaned.jsonl", literature["normalized"])
    write_jsonl(paths["literature_root"] / "kb_b_literature.cleaned.jsonl", literature["kb_b_literature"])
    write_json(paths["literature_root"] / "literature_index.cleaned.json", literature["literature_index"])
    for index, row in enumerate(literature["normalized"], start=1):
        stem = sanitize_filename(row.get("title"), f"doc_{index}")
        (paths["literature_text_root"] / f"{stem}.txt").write_text(row["content"], encoding="utf-8")

    write_json(paths["mappings_root"] / "element_literature_map.cleaned.json", mapping)
    write_json(paths["kg_root"] / "entities.cleaned.json", kg["entities"])
    write_json(paths["kg_root"] / "relations.cleaned.json", kg["relations"])
    write_json(paths["kg_root"] / "triples.cleaned.json", kg["triples"])
    write_json(paths["kg_root"] / "alias_index.cleaned.json", kg["alias_index"])


def build_cleaning_summary(elements: dict, literature: dict, mapping: dict, kg: dict, exceptions: list[dict]) -> dict:
    issue_counts = {}
    for item in exceptions:
        issue_counts[item["issue_type"]] = issue_counts.get(item["issue_type"], 0) + 1
    counts = {
        **elements["counts"],
        **literature["counts"],
        **kg["counts"],
        "mapping_elements_cleaned": mapping.get("element_count", 0),
        "mapping_total_links": mapping.get("total_links", 0),
        "exceptions_total": len(exceptions),
    }
    return {
        "counts": counts,
        "issue_counts": issue_counts,
        "retention": {
            "entities": round(kg["counts"]["entities_cleaned"] / max(kg["counts"]["entities_raw"], 1), 4),
            "relations": round(kg["counts"]["relations_cleaned"] / max(kg["counts"]["relations_raw"], 1), 4),
            "triples": round(kg["counts"]["triples_cleaned"] / max(kg["counts"]["triples_raw"], 1), 4),
        },
    }


def build_validation_summary(
    paths: dict[str, Path],
    elements: dict,
    literature: dict,
    mapping: dict,
    kg: dict,
    exceptions: list[dict],
    sample_limit: int,
) -> dict:
    required_paths = [
        paths["elements_root"] / "element_index.cleaned.json",
        paths["literature_root"] / "normalized.cleaned.jsonl",
        paths["mappings_root"] / "element_literature_map.cleaned.json",
        paths["kg_root"] / "entities.cleaned.json",
        paths["reports_root"] / "exceptions.jsonl",
    ]
    file_checks = {str(path): path.exists() for path in required_paths}
    unique_elements = len(elements["element_index"]) == len(set(elements["element_index"].keys()))
    doi_values = [row["doi"] for row in literature["normalized"] if row.get("doi")]
    url_values = [row["url"] for row in literature["normalized"] if row.get("url")]
    link_values = [ref for refs in mapping.get("linkage", {}).values() for ref in refs]
    relation_noise_samples = [
        item for item in exceptions if item["issue_type"] in {"noise_entity_filtered", "broken_relation_filtered"}
    ][:sample_limit]
    validation = {
        "file_checks": file_checks,
        "unique_elements": unique_elements,
        "unique_doi_count": len(set(doi_values)),
        "doi_count": len(doi_values),
        "unique_url_count": len(set(url_values)),
        "url_count": len(url_values),
        "mapping_element_hit_rate": round(mapping.get("linked_elements", 0) / max(mapping.get("element_count", 0), 1), 4),
        "mapping_literature_hit_rate": round(len(link_values) / max(mapping.get("total_links", 0), 1), 4) if mapping.get("total_links", 0) else 1.0,
        "empty_subject_or_object_relations": sum(
            1 for relation in kg["relations"] if not relation.get("subject") or not relation.get("object")
        ),
        "noise_samples": relation_noise_samples,
    }
    validation["passed"] = all(file_checks.values()) and unique_elements and validation["empty_subject_or_object_relations"] == 0
    return validation


def run_cleaning(
    zip_path: Path,
    output_root: Path,
    min_relation_confidence: float = 0.8,
    overwrite: bool = False,
    sample_limit: int = 20,
) -> dict:
    zip_path = Path(zip_path)
    paths = prepare_output_dirs(Path(output_root), overwrite=overwrite)
    exceptions: list[dict] = []

    with zipfile.ZipFile(zip_path) as zf:
        domain_vocab = load_json_from_zip(zf, "data_2/data/domain_vocab.json")
        kb_elements = load_json_from_zip(zf, "data_2/data/kb_exports/kb_a_elements.json")
        raw_map = load_json_from_zip(zf, "data_2/data/kb_exports/element_literature_map.json")
        exported_docs = load_jsonl_from_zip(zf, "data_2/data/kb_exports/kb_b_literature.jsonl")
        normalized_docs = load_normalized_documents(zf)
        entities_payload = load_json_from_zip(zf, "data_2/data/kg_output/entities.json")
        relations_payload = load_json_from_zip(zf, "data_2/data/kg_output/relations.json")
        triples_payload = load_json_from_zip(zf, "data_2/data/kg_output/triples.json")

    elements = clean_elements(domain_vocab, kb_elements, exceptions)
    literature = clean_literature(normalized_docs, exported_docs, exceptions)
    mapping = clean_element_literature_map(raw_map, elements["element_index"], literature["literature_index"], exceptions)
    kg = clean_kg(
        entities_payload,
        relations_payload,
        triples_payload,
        elements["element_index"],
        exceptions,
        min_confidence=min_relation_confidence,
    )

    write_cleaned_outputs(paths, elements, literature, mapping, kg)
    cleaning_summary = build_cleaning_summary(elements, literature, mapping, kg, exceptions)
    write_json(paths["reports_root"] / "cleaning_summary.json", cleaning_summary)
    write_jsonl(paths["reports_root"] / "exceptions.jsonl", exceptions)
    validation = build_validation_summary(paths, elements, literature, mapping, kg, exceptions, sample_limit)
    write_json(paths["reports_root"] / "validation_summary.json", validation)

    return {
        "zip_path": str(zip_path),
        "output_root": str(paths["output_root"]),
        "summary": cleaning_summary,
        "validation": validation,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_cleaning(
        Path(args.zip_path),
        Path(args.output_root),
        min_relation_confidence=args.min_relation_confidence,
        overwrite=args.overwrite,
        sample_limit=args.sample_limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
