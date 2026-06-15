#!/usr/bin/env python3
"""Validate catalog.jsonl quality and sync with references.bib and references.csl.json.

Usage:
    python scripts/validate_catalog.py --project /path/to/project
    python scripts/validate_catalog.py --project /path/to/project --output report.md
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literature_store import read_catalog, validate_record
from export_references import _extract_bib_citekeys, _extract_csl_ids
from dedup import normalize_doi


def _find_project_root() -> Path:
    current = Path.cwd().resolve()
    for _ in range(10):
        if (current / ".paper-workflow").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise FileNotFoundError("找不到 .paper-workflow/ 目录。")


def _is_valid_doi_format(doi: str) -> bool:
    """Check if a DOI string looks well-formed."""
    ndoi = normalize_doi(doi)
    if ndoi is None:
        return False
    return ndoi.startswith("10.") and "/" in ndoi


def validate_catalog(project_dir: Path | None = None) -> dict[str, Any]:
    """Validate catalog.jsonl against schema, uniqueness, and bib/csl sync.

    Returns:
        {
            "total_records": int,
            "errors": [str, ...],
            "warnings": [str, ...],
        }
    """
    root = project_dir or _find_project_root()
    records = read_catalog(root)

    errors: list[str] = []
    warnings: list[str] = []

    if not records:
        warnings.append("catalog.jsonl 为空")
        return {
            "total_records": 0,
            "errors": errors,
            "warnings": warnings,
        }

    total = len(records)

    # 1. Schema validation per record
    schema_errors = 0
    for record in records:
        cid = record.get("canonical_id", "?")
        errs = validate_record(record)
        if errs:
            schema_errors += 1
            for e in errs:
                errors.append(f"[{cid}] schema 校验失败: {e}")
    if schema_errors == 0:
        pass  # All valid — no message needed

    # 2. canonical_id uniqueness
    cids = [r.get("canonical_id") for r in records]
    cid_counts: dict[str, int] = {}
    for cid in cids:
        if cid:
            cid_counts[cid] = cid_counts.get(cid, 0) + 1
    for cid, count in cid_counts.items():
        if count > 1:
            errors.append(f"重复 canonical_id: {cid} 出现 {count} 次")

    # 3. citekey uniqueness
    citekeys = [r.get("citekey") for r in records]
    ck_counts: dict[str, int] = {}
    for ck in citekeys:
        if ck:
            ck_counts[ck] = ck_counts.get(ck, 0) + 1
    for ck, count in ck_counts.items():
        if count > 1:
            errors.append(f"重复 citekey: {ck} 出现 {count} 次")

    # 4. DOI format validation
    doi_issues = 0
    missing_doi = 0
    for record in records:
        cid = record.get("canonical_id", "?")
        doi = record.get("doi")
        if not doi:
            missing_doi += 1
            continue
        if not _is_valid_doi_format(str(doi)):
            doi_issues += 1
            warnings.append(f"[{cid}] DOI 格式异常: {doi}")
    if missing_doi > 0:
        warnings.append(f"{missing_doi} 条记录缺少 DOI")
    if doi_issues > 0:
        warnings.append(f"{doi_issues} 条记录 DOI 格式异常")

    # 5. Core field checks
    missing_title = sum(1 for r in records if not r.get("title"))
    missing_authors = sum(1 for r in records if not r.get("authors"))
    missing_year = sum(1 for r in records if not r.get("year"))
    if missing_title:
        errors.append(f"{missing_title} 条记录缺少标题")
    if missing_authors:
        errors.append(f"{missing_authors} 条记录缺少作者")
    if missing_year:
        warnings.append(f"{missing_year} 条记录缺少年份")

    # 6. Bib/CSL sync check
    bib_path = root / "literature" / "references.bib"
    csl_path = root / "literature" / "references.csl.json"

    if bib_path.exists():
        bib_keys = set(_extract_bib_citekeys(bib_path))
        cat_keys = set(ck for ck in citekeys if ck)
        only_bib = bib_keys - cat_keys
        only_cat = cat_keys - bib_keys
        if only_bib:
            errors.append(f"references.bib 中有 {len(only_bib)} 条不在 catalog 中: {', '.join(sorted(only_bib)[:5])}")
        if only_cat:
            errors.append(f"catalog 中有 {len(only_cat)} 条不在 references.bib 中: {', '.join(sorted(only_cat)[:5])}")
    else:
        warnings.append("references.bib 不存在")

    if csl_path.exists():
        csl_ids = set(_extract_csl_ids(csl_path))
        cat_keys = set(ck for ck in citekeys if ck)
        only_csl = csl_ids - cat_keys
        only_cat2 = cat_keys - csl_ids
        if only_csl:
            errors.append(f"references.csl.json 中有 {len(only_csl)} 条不在 catalog 中")
        if only_cat2:
            errors.append(f"catalog 中有 {len(only_cat2)} 条不在 references.csl.json 中")
    else:
        warnings.append("references.csl.json 不存在")

    return {
        "total_records": total,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Validate catalog quality")
    parser.add_argument("--project", help="Paper project root directory")
    parser.add_argument("--output", help="Output Markdown report path")
    args = parser.parse_args()

    project_dir = Path(args.project) if args.project else _find_project_root()
    result = validate_catalog(project_dir)

    lines = [
        "# 文献库质量校验报告",
        "",
        f"**总记录数**: {result['total_records']}",
        "",
        f"## Errors ({len(result['errors'])})",
        "",
    ]
    if result["errors"]:
        for e in result["errors"]:
            lines.append(f"- ❌ {e}")
    else:
        lines.append("- ✅ 无错误")
    lines.append("")

    lines.append(f"## Warnings ({len(result['warnings'])})")
    lines.append("")
    if result["warnings"]:
        for w in result["warnings"]:
            lines.append(f"- ⚠ {w}")
    else:
        lines.append("- ✅ 无警告")
    lines.append("")

    report = "\n".join(lines)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

    print(report)
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
