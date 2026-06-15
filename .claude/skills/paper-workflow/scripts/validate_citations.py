#!/usr/bin/env python3
"""Validate citation consistency: manuscript ↔ bibliography ↔ claim map.

Usage:
    python scripts/validate_citations.py \\
        --manuscript manuscript/main.md \\
        --bib literature/references.bib \\
        --claim-map citations/claim-citation-map.csv
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_references import _extract_bib_citekeys, find_duplicate_citekeys


# ---------------------------------------------------------------------------
# Citation extraction from Markdown
# ---------------------------------------------------------------------------

_PANDOC_CITE_PATTERN = re.compile(
    r"""
    (?:\[(-)?@([^\[\]]+?)\])   # [@key] or [-@key] or [@key1; @key2]
    |
    (?<!\w)@([a-zA-Z][\w:.#$%&\-+?<>~/]*[a-zA-Z0-9)])  # standalone @key
    """,
    re.VERBOSE,
)


def extract_markdown_citations(manuscript_path: Path) -> set[str]:
    """Extract all citekeys from a Pandoc Markdown manuscript.

    Supports: [@key], [@key1; @key2], [-@key], @key
    """
    if not manuscript_path.exists():
        return set()

    text = manuscript_path.read_text(encoding="utf-8")
    citekeys = set()

    for match in _PANDOC_CITE_PATTERN.finditer(text):
        bracket_keys = match.group(2)  # [@...] or [-@...]
        standalone_key = match.group(3)  # @key

        if bracket_keys:
            # Split on semicolons and strip
            for key in bracket_keys.split(";"):
                key = key.strip().lstrip("@")
                if key:
                    citekeys.add(key)
        elif standalone_key:
            citekeys.add(standalone_key)

    return citekeys


# ---------------------------------------------------------------------------
# [CITE NEEDED] detection
# ---------------------------------------------------------------------------

_CITE_NEEDED_PATTERN = re.compile(r"\[CITE\s*NEEDED\]", re.IGNORECASE)


def find_cite_needed(manuscript_path: Path) -> list[dict]:
    """Find all [CITE NEEDED] occurrences with line numbers."""
    if not manuscript_path.exists():
        return []
    results = []
    with open(manuscript_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            for match in _CITE_NEEDED_PATTERN.finditer(line):
                # Get surrounding context
                start = max(0, match.start() - 30)
                end = min(len(line), match.end() + 30)
                context = line[start:end].strip()
                results.append({
                    "line": line_num,
                    "column": match.start() + 1,
                    "context": f"...{context}...",
                })
    return results


# ---------------------------------------------------------------------------
# Citekey consistency
# ---------------------------------------------------------------------------

def check_citekey_consistency(
    manuscript_path: Path,
    bib_path: Path,
) -> dict[str, Any]:
    """Check that all citekeys in the manuscript are in the bibliography.

    Returns:
        {
            "used_in_text": [str],
            "available_in_bib": [str],
            "missing_in_bib": [str],
            "unused_in_text": [str],
        }
    """
    text_keys = extract_markdown_citations(manuscript_path)
    bib_keys = set(_extract_bib_citekeys(bib_path))

    missing = sorted(text_keys - bib_keys)
    unused = sorted(bib_keys - text_keys)

    return {
        "used_in_text": sorted(text_keys),
        "available_in_bib": sorted(bib_keys),
        "missing_in_bib": missing,
        "unused_in_text": unused,
    }


def check_duplicate_citekeys_wrapper(bib_path: Path) -> list[str]:
    """Wrapper for find_duplicate_citekeys from export_references."""
    return find_duplicate_citekeys(bib_path)


# ---------------------------------------------------------------------------
# Cross-check with claim-citation-map
# ---------------------------------------------------------------------------

def _read_claim_map(claim_map_path: Path) -> list[dict]:
    """Read claim-citation-map.csv."""
    if not claim_map_path.exists():
        return []
    with open(claim_map_path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _extract_all_supporting_citekeys(claim_map_path: Path) -> set[str]:
    """Extract all citekeys referenced in the claim map."""
    rows = _read_claim_map(claim_map_path)
    keys = set()
    for row in rows:
        sc = row.get("supporting_citekeys", "")
        for k in sc.split(";"):
            k = k.strip()
            if k:
                keys.add(k)
    return keys


def cross_check_citations(
    manuscript_path: Path,
    claim_map_path: Path,
) -> dict[str, Any]:
    """Cross-check: manuscript citekeys vs claim-map supporting citekeys.

    Returns:
        {
            "manuscript_citekeys": [str],
            "claim_map_citekeys": [str],
            "in_manuscript_not_in_claim_map": [str],  # evidence gap
            "in_claim_map_not_in_manuscript": [str],
        }
    """
    text_keys = extract_markdown_citations(manuscript_path)
    claim_keys = _extract_all_supporting_citekeys(claim_map_path)

    evidence_gap = sorted(text_keys - claim_keys)
    unused_evidence = sorted(claim_keys - text_keys)

    return {
        "manuscript_citekeys": sorted(text_keys),
        "claim_map_citekeys": sorted(claim_keys),
        "in_manuscript_not_in_claim_map": evidence_gap,
        "in_claim_map_not_in_manuscript": unused_evidence,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _format_report(results: dict[str, Any]) -> str:
    """Format validation results as Markdown."""
    lines = ["# 引文一致性校验报告", ""]

    # Citekey consistency
    if "missing_in_bib" in results:
        lines.append("## 正文引用 ↔ 参考文献库")
        lines.append("")
        missing = results["missing_in_bib"]
        unused = results["unused_in_text"]
        lines.append(f"- 正文引用: {len(results['used_in_text'])} 个")
        lines.append(f"- 参考文献库: {len(results['available_in_bib'])} 条")
        if missing:
            lines.append(f"- ⚠ 缺失引用 ({len(missing)}): {', '.join(missing)}")
        if unused:
            lines.append(f"- ⚠ 未使用文献 ({len(unused)}): {', '.join(unused)}")
        if not missing and not unused:
            lines.append("- ✅ 全部一致")
        lines.append("")

    # Duplicate citekeys
    if "duplicate_citekeys" in results:
        dupes = results["duplicate_citekeys"]
        lines.append("## 重复 citekey")
        lines.append("")
        if dupes:
            lines.append(f"- ⚠ {len(dupes)} 个重复: {', '.join(dupes)}")
        else:
            lines.append("- ✅ 无重复")
        lines.append("")

    # Cross-check
    if "in_manuscript_not_in_claim_map" in results:
        lines.append("## 正文引用 ↔ 证据矩阵")
        lines.append("")
        gap = results["in_manuscript_not_in_claim_map"]
        unused_ev = results["in_claim_map_not_in_manuscript"]
        if gap:
            lines.append(f"- ⚠ 正文使用但不在 evidence matrix 中的引用 ({len(gap)}): {', '.join(gap)}")
        if unused_ev:
            lines.append(f"- ⚠ 证据矩阵中有但正文未使用的引用 ({len(unused_ev)}): {', '.join(unused_ev)}")
        if not gap and not unused_ev:
            lines.append("- ✅ 正文字引用与证据矩阵一致")
        lines.append("")

    # [CITE NEEDED]
    if "cite_needed" in results:
        cn = results["cite_needed"]
        lines.append("## [CITE NEEDED] 残留")
        lines.append("")
        if cn:
            lines.append(f"发现 {len(cn)} 处 [CITE NEEDED]：")
            for item in cn:
                lines.append(f"- 第 {item['line']} 行: `{item['context']}`")
        else:
            lines.append("- ✅ 无 [CITE NEEDED] 残留")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate citation consistency")
    parser.add_argument("--manuscript", help="Path to manuscript/main.md")
    parser.add_argument("--bib", help="Path to references.bib")
    parser.add_argument("--claim-map", help="Path to claim-citation-map.csv")
    parser.add_argument("--output", help="Output Markdown report path")
    args = parser.parse_args()

    results: dict[str, Any] = {}

    # 1. Citekey consistency
    if args.manuscript and args.bib:
        manuscript_path = Path(args.manuscript)
        bib_path = Path(args.bib)
        if manuscript_path.exists() and bib_path.exists():
            consistency = check_citekey_consistency(manuscript_path, bib_path)
            results.update(consistency)

            # Duplicate check
            dupes = check_duplicate_citekeys_wrapper(bib_path)
            results["duplicate_citekeys"] = dupes

            # [CITE NEEDED]
            cn = find_cite_needed(manuscript_path)
            results["cite_needed"] = cn

    # 2. Cross-check with claim map
    if args.manuscript and args.claim_map:
        manuscript_path = Path(args.manuscript)
        claim_map_path = Path(args.claim_map)
        if manuscript_path.exists() and claim_map_path.exists():
            cross = cross_check_citations(manuscript_path, claim_map_path)
            results.update(cross)

    report = _format_report(results)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"报告已输出: {args.output}")
    else:
        print(report)

    # Return non-zero if issues found
    has_issues = (
        len(results.get("missing_in_bib", [])) > 0
        or len(results.get("duplicate_citekeys", [])) > 0
        or len(results.get("cite_needed", [])) > 0
        or len(results.get("in_manuscript_not_in_claim_map", [])) > 0
    )
    return 1 if has_issues else 0


if __name__ == "__main__":
    sys.exit(main())
