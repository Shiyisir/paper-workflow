#!/usr/bin/env python3
"""Literature deduplication engine.

5-level dedup:
  1. DOI exact match (after normalization)
  2. Normalized title exact match + same year
  3. Title similarity ≥ 0.85 + first author match + year diff ≤ 1
  4. Author group + journal + volume/pages match
  5. Cross-language / arXiv ID → related_versions (never auto-delete)

Usage:
    python scripts/dedup.py --catalog literature/catalog.jsonl
    python scripts/dedup.py --catalog literature/catalog.jsonl --output literature/catalog.deduped.jsonl
    python scripts/dedup.py --catalog literature/catalog.jsonl --output catalog.deduped.jsonl --report literature/dedup-report.md
"""

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# DOI normalization
# ---------------------------------------------------------------------------

def normalize_doi(raw: str | None) -> str | None:
    """Normalize a DOI string to lowercase '10.xxxx/...' format.

    Returns None for empty, invalid, or unparseable DOIs.
    Never raises.
    """
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None

    # Decode URL encoding
    s = re.sub(r"%([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), s)

    # Remove common prefixes
    for prefix in [
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
        "DOI:",
        "doi ",
        "DOI ",
        "https://hdl.handle.net/",
    ]:
        if s.lower().startswith(prefix.lower()):
            s = s[len(prefix):]
            break

    # Strip whitespace again after prefix removal
    s = s.strip().lower()

    # Must start with '10.' and contain '/'
    if not s.startswith("10.") or "/" not in s:
        return None

    # Remove trailing punctuation and whitespace
    s = re.sub(r"[\s.,;:!?\)\]}]+$", "", s)

    # Truncate excessively long DOIs
    if len(s) > 500:
        return None

    return s


# ---------------------------------------------------------------------------
# Title normalization
# ---------------------------------------------------------------------------

def normalize_title(title: str) -> str:
    """Normalize a title for comparison.

    - Lowercase
    - Remove punctuation except letters and digits
    - Collapse whitespace
    - Normalize quotes
    """
    if not title:
        return ""
    s = title.lower()
    # Normalize curly/smart quotes to straight
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("“", '"').replace("”", '"')
    # Remove everything except letters, digits, and spaces
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def title_similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two normalized titles."""
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


# ---------------------------------------------------------------------------
# Author matching
# ---------------------------------------------------------------------------

def _extract_last_name(author: str) -> str:
    """Extract last name from author string."""
    if "," in author:
        return author.split(",")[0].strip().lower()
    parts = author.strip().split()
    return parts[-1].lower() if parts else author.strip().lower()


def first_author_match(authors_a: list[str], authors_b: list[str]) -> bool:
    """Check if the first authors match (last name comparison)."""
    if not authors_a or not authors_b:
        return False
    return _extract_last_name(authors_a[0]) == _extract_last_name(authors_b[0])


def author_group_match(authors_a: list[str], authors_b: list[str]) -> bool:
    """Check if author groups roughly match (≥ 50% overlap of last names)."""
    if not authors_a or not authors_b:
        return False
    set_a = {_extract_last_name(a) for a in authors_a}
    set_b = {_extract_last_name(a) for a in authors_b}
    if not set_a or not set_b:
        return False
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) >= 0.5


# ---------------------------------------------------------------------------
# Version and language detection
# ---------------------------------------------------------------------------

def _detect_arxiv_id(record: dict) -> str | None:
    """Extract arXiv ID from a record if present."""
    doi = (record.get("doi") or "").lower()
    if "arxiv" in doi:
        # arxiv DOI format: 10.48550/arXiv.2401.12345
        parts = doi.split("/")
        if len(parts) >= 2:
            return parts[-1].lower().replace("arxiv.", "")
    # Check sources
    for src in record.get("sources", []):
        if src.lower() == "arxiv":
            # Try to get ID from title or notes
            pass
    # Check related_versions
    for rv in record.get("related_versions", []):
        if rv.get("source", "").lower() == "arxiv":
            return rv.get("id", "").lower()
    return None


def _is_preprint(record: dict) -> bool:
    """Heuristic: detect if a record is likely a preprint."""
    title = (record.get("title") or "").lower()
    preprint_markers = ["preprint", "arxiv:", "arxiv"]
    for marker in preprint_markers:
        if marker in title:
            return True
    return bool(_detect_arxiv_id(record))


def _likely_same_language(a: dict, b: dict) -> bool:
    """Check if two records are likely in the same language."""
    la = a.get("language", "")
    lb = b.get("language", "")
    if la and lb and la != lb:
        return False
    return True


# ---------------------------------------------------------------------------
# Source merging
# ---------------------------------------------------------------------------

def _merge_sources(records: list[dict]) -> dict:
    """Merge multiple records representing the same paper into one.

    Keeps the most complete metadata while merging sources.
    """
    if len(records) == 1:
        return records[0]

    # Start with the record that has the most non-null fields
    def _field_count(r: dict) -> int:
        count = 0
        for k, v in r.items():
            if k in ("sources", "related_versions"):
                continue
            if v is not None and v != "" and v != []:
                count += 1
        return count

    best = max(records, key=_field_count)

    # Merge sources
    all_sources = set()
    for r in records:
        for s in r.get("sources", []):
            all_sources.add(s)
    best["sources"] = sorted(all_sources)

    # Merge related_versions
    all_versions = {}
    for r in records:
        for rv in r.get("related_versions", []):
            vid = (rv.get("source", ""), rv.get("id", ""))
            if vid not in all_versions:
                all_versions[vid] = rv
    best["related_versions"] = list(all_versions.values())

    # Keep the better screening status
    statuses = [r.get("screening_status") for r in records]
    if "included" in statuses:
        best["screening_status"] = "included"
    elif "maybe" in statuses and "excluded" not in statuses:
        best["screening_status"] = "maybe"

    return best


# ---------------------------------------------------------------------------
# Main dedup logic
# ---------------------------------------------------------------------------

def deduplicate(records: list[dict]) -> dict:
    """Deduplicate a list of literature records.

    Returns:
        {
            "unique": list[dict],        # Deduplicated records
            "merged": list[dict],        # Records formed by merging sources
            "related": list[dict],       # Related version pairs
            "pending_review": list[dict], # Cross-language / uncertain pairs
        }
    """
    if not records:
        return {
            "unique": [],
            "merged": [],
            "related": [],
            "pending_review": [],
        }

    remaining = list(records)
    unique = []
    merged_groups = []
    related_pairs = []
    pending_pairs = []

    # Pre-index by DOI
    doi_index: dict[str, list[int]] = {}
    for i, r in enumerate(remaining):
        ndoi = normalize_doi(r.get("doi"))
        if ndoi:
            doi_index.setdefault(ndoi, []).append(i)

    # --- Level 1: DOI exact match ---
    doi_matched = set()
    for doi, indices in doi_index.items():
        if len(indices) >= 2:
            group = [remaining[i] for i in indices]
            merged = _merge_sources(group)
            merged_groups.append(group)
            unique.append(merged)
            if len(group) == 2 and _is_preprint(group[0]) != _is_preprint(group[1]):
                related_pairs.append({
                    "records": [r["canonical_id"] for r in group],
                    "relation": "preprint_of" if _is_preprint(group[0]) else "published_version_of",
                    "reason": "DOI match: one is preprint, one is published",
                })
            for i in indices:
                doi_matched.add(i)

    # --- Level 2: Normalized title + same year ---
    l2_matched = set()
    for i in range(len(remaining)):
        if i in doi_matched or i in l2_matched:
            continue
        group = [remaining[i]]
        group_indices = [i]
        for j in range(i + 1, len(remaining)):
            if j in doi_matched or j in l2_matched:
                continue
            a, b = remaining[i], remaining[j]
            na = normalize_title(a.get("title", ""))
            nb = normalize_title(b.get("title", ""))
            if na and nb and na == nb and a.get("year") == b.get("year"):
                group.append(remaining[j])
                group_indices.append(j)
        if len(group) >= 2:
            for idx in group_indices:
                l2_matched.add(idx)
            merged = _merge_sources(group)
            merged_groups.append(group)
            unique.append(merged)
        elif len(group) == 1:
            pass  # Solo records pass through to next level

    # Collect residual after L1+L2 (only solos that didn't merge in L2)
    residual_l2 = [remaining[i] for i in range(len(remaining))
                   if i not in doi_matched and i not in l2_matched]

    # --- Level 3: Title similarity + first author + year close ---
    l3_matched = set()
    for i in range(len(residual_l2)):
        if i in l3_matched:
            continue
        a = residual_l2[i]
        group = [a]
        group_indices = [i]
        for j in range(i + 1, len(residual_l2)):
            if j in l3_matched:
                continue
            b = residual_l2[j]
            sim = title_similarity(a.get("title", ""), b.get("title", ""))
            year_a = a.get("year") or 0
            year_b = b.get("year") or 0
            if (sim >= 0.85
                    and first_author_match(a.get("authors", []), b.get("authors", []))
                    and abs(year_a - year_b) <= 1):
                group.append(b)
                group_indices.append(j)
        if len(group) >= 2:
            for idx in group_indices:
                l3_matched.add(idx)
            merged = _merge_sources(group)
            merged_groups.append(group)
            unique.append(merged)

    # Collect residual after L3
    residual_l3 = [residual_l2[i] for i in range(len(residual_l2)) if i not in l3_matched]

    # --- Level 4: Author group + journal + volume/pages ---
    l4_matched = set()
    for i in range(len(residual_l3)):
        if i in l4_matched:
            continue
        a = residual_l3[i]
        group = [a]
        group_indices = [i]
        for j in range(i + 1, len(residual_l3)):
            if j in l4_matched:
                continue
            b = residual_l3[j]
            if (author_group_match(a.get("authors", []), b.get("authors", []))
                    and a.get("journal") == b.get("journal")
                    and a.get("journal") is not None
                    and (a.get("volume") == b.get("volume") or a.get("pages") == b.get("pages"))):
                group.append(b)
                group_indices.append(j)
        if len(group) >= 2:
            for idx in group_indices:
                l4_matched.add(idx)
            merged = _merge_sources(group)
            merged_groups.append(group)
            unique.append(merged)

    # Remaining solos after all levels → unique
    residual_l4 = [residual_l3[i] for i in range(len(residual_l3)) if i not in l4_matched]
    unique.extend(residual_l4)

    # --- Level 5: Cross-language / arXiv detection ---
    # Check among unique records for cross-language duplicates
    for i in range(len(unique)):
        for j in range(i + 1, len(unique)):
            a, b = unique[i], unique[j]
            sim = title_similarity(a.get("title", ""), b.get("title", ""))

            # High title similarity but different languages → pending_review
            if sim >= 0.70 and not _likely_same_language(a, b):
                pending_pairs.append({
                    "record_a": a["canonical_id"],
                    "record_b": b["canonical_id"],
                    "similarity": round(sim, 3),
                    "reason": f"标题高度相似 (sim={sim:.2f}) 但语言不同，疑似跨语言重复",
                })

            # arXiv preprint and published version
            aid = _detect_arxiv_id(a)
            bid = _detect_arxiv_id(b)
            if aid and bid and aid == bid:
                related_pairs.append({
                    "records": [a["canonical_id"], b["canonical_id"]],
                    "relation": "same_arxiv_id",
                    "reason": f"同一 arXiv ID: {aid}",
                })
            elif sim >= 0.85 and (_is_preprint(a) != _is_preprint(b)):
                related_pairs.append({
                    "records": [a["canonical_id"], b["canonical_id"]],
                    "relation": "preprint_published",
                    "reason": f"高度相似的标题—一篇可能是预印本，另一篇是正式发表版 (sim={sim:.3f})",
                })

    return {
        "unique": unique,
        "merged": merged_groups,
        "related": related_pairs,
        "pending_review": pending_pairs,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_catalog(path: str) -> list[dict]:
    """Load catalog.jsonl."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def _save_catalog(records: list[dict], path: str) -> None:
    """Save deduped records to JSONL."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Deduplicate literature catalog")
    parser.add_argument("--catalog", required=True, help="Path to catalog.jsonl")
    parser.add_argument("--output", help="Path for deduped output JSONL")
    parser.add_argument("--report", help="Path for dedup report (Markdown)")
    args = parser.parse_args()

    records = _load_catalog(args.catalog)
    original_count = len(records)
    print(f"读取 {original_count} 条文献记录")

    result = deduplicate(records)

    unique_count = len(result["unique"])
    merged_count = sum(len(g) - 1 for g in result["merged"])
    related_count = len(result["related"])
    pending_count = len(result["pending_review"])

    print(f"去重后: {unique_count} 条唯一文献")
    print(f"  DOI 合并: {merged_count} 条")
    print(f"  关联版本: {related_count} 组")
    print(f"  待审核: {pending_count} 项")

    if args.output:
        _save_catalog(result["unique"], args.output)
        print(f"已输出: {args.output}")

    if args.report:
        from pathlib import Path as _Path
        report_path = _Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = _generate_report(result, original_count, unique_count)
        report_path.write_text(report, encoding="utf-8")
        print(f"已输出报告: {args.report}")

    return 0


# ---------------------------------------------------------------------------
# Report generation (shared with M3.3)
# ---------------------------------------------------------------------------

def _generate_report(result: dict, original_count: int, unique_count: int) -> str:
    """Generate a Markdown dedup report."""
    lines = [
        "# 文献去重报告",
        "",
        f"**原始文献条数**: {original_count}",
        f"**去重后文献条数**: {unique_count}",
        f"**去重率**: {original_count - unique_count} 条被合并 ({100 * (original_count - unique_count) / max(original_count, 1):.1f}%)",
        "",
        "## 统计摘要",
        "",
        f"| 类别 | 数量 |",
        f"|------|:---:|",
        f"| DOI 精确匹配合并 | {sum(1 for g in result['merged'] if len(g) >= 2) | 0} |",
        f"| 关联版本 | {len(result['related'])} |",
        f"| 待人工审核 | {len(result['pending_review'])} |",
        "",
    ]

    # Merged records
    if result["merged"]:
        lines.append("## 合并记录")
        lines.append("")
        for gi, group in enumerate(result["merged"], 1):
            cids = [r.get("canonical_id", "?") for r in group]
            titles = [r.get("title", "?")[:60] for r in group]
            sources = [s for r in group for s in r.get("sources", [])]
            lines.append(f"### 合并组 {gi}: {', '.join(cids)}")
            lines.append("")
            for cid, title in zip(cids, titles):
                lines.append(f"- **{cid}**: {title}")
            lines.append(f"- 合并来源: {', '.join(sorted(set(sources)))}")
            lines.append("")

    # Related versions
    if result["related"]:
        lines.append("## 关联版本")
        lines.append("")
        for ri, rel in enumerate(result["related"], 1):
            cids = rel.get("records", [])
            lines.append(f"- **{ri}.** {', '.join(cids)} — {rel.get('reason', '')}")
        lines.append("")

    # Pending review
    if result["pending_review"]:
        lines.append("## 待人工审核")
        lines.append("")
        for pi, pending in enumerate(result["pending_review"], 1):
            lines.append(f"### 审核项 {pi}")
            lines.append(f"- 文献 A: `{pending.get('record_a', '?')}`")
            lines.append(f"- 文献 B: `{pending.get('record_b', '?')}`")
            lines.append(f"- 相似度: {pending.get('similarity', '?')}")
            lines.append(f"- 理由: {pending.get('reason', '?')}")
            lines.append("")

    if not result["merged"] and not result["related"] and not result["pending_review"]:
        lines.append("未发现重复文献。")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
