#!/usr/bin/env python3
"""Export references from catalog.jsonl to BibTeX and CSL JSON.

Usage:
    python scripts/export_references.py --project /path/to/project --format both
    python scripts/export_references.py --project /path/to/project --format bib
    python scripts/export_references.py --project /path/to/project --format csl
"""

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from literature_store import read_catalog


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


# ---------------------------------------------------------------------------
# BibTeX export
# ---------------------------------------------------------------------------

def _escape_bibtex(text: str) -> str:
    """Escape special characters for BibTeX."""
    if not text:
        return ""
    # Replace LaTeX special chars
    for char in ["&", "%", "$", "#", "_", "{", "}"]:
        text = text.replace(char, "\\" + char)
    # Already-escaped sequences shouldn't be double-escaped
    text = text.replace("\\\\", "\\")
    return text


def _record_to_bibtex(record: dict) -> str:
    """Convert a single literature record to a BibTeX entry."""
    citekey = record.get("citekey", "unknown")
    title = record.get("title", "")
    authors = record.get("authors", [])
    year = record.get("year", "")
    doi = record.get("doi", "")
    journal = record.get("journal", "")
    volume = record.get("volume", "")
    pages = record.get("pages", "")

    # Determine entry type
    entry_type = "article"  # default
    keywords = " ".join(record.get("keywords", []))
    # Heuristic: if no journal, might be a book or misc
    if not journal and not volume:
        entry_type = "misc"

    # Format authors for BibTeX
    author_str = " and ".join(authors) if authors else ""

    lines = [f"@{entry_type}{{{citekey},"]
    if author_str:
        lines.append(f"  author = {{{_escape_bibtex(author_str)}}},")
    else:
        warnings.warn(f"BibTeX: citekey '{citekey}' missing authors")

    if title:
        lines.append(f"  title = {{{_escape_bibtex(title)}}},")
    else:
        warnings.warn(f"BibTeX: citekey '{citekey}' missing title")

    if year:
        lines.append(f"  year = {{{year}}},")
    else:
        warnings.warn(f"BibTeX: citekey '{citekey}' missing year")

    if journal:
        lines.append(f"  journal = {{{_escape_bibtex(journal)}}},")
    if volume:
        lines.append(f"  volume = {{{volume}}},")
    if pages:
        lines.append(f"  pages = {{{pages}}},")
    if doi:
        lines.append(f"  doi = {{{doi}}},")
    if keywords:
        lines.append(f"  keywords = {{{_escape_bibtex(keywords)}}},")

    lines.append("}")
    return "\n".join(lines)


def export_bib(project_dir: Path | None = None, output_path: Path | None = None) -> int:
    """Export catalog.jsonl to references.bib.

    Returns the number of entries exported.
    """
    root = project_dir or _find_project_root()
    records = read_catalog(root)

    if not records:
        print("警告: catalog.jsonl 为空，未生成任何 BibTeX 条目")
        return 0

    bib_path = output_path or (root / "literature" / "references.bib")
    bib_path.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    for record in records:
        citekey = record.get("citekey")
        if not citekey:
            warnings.warn(f"跳过: canonical_id={record.get('canonical_id', '?')} 缺少 citekey")
            continue
        entries.append(_record_to_bibtex(record))

    with open(bib_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(entries) + "\n")

    print(f"已导出 {len(entries)} 条 BibTeX 记录到 {bib_path}")
    return len(entries)


# ---------------------------------------------------------------------------
# CSL JSON export
# ---------------------------------------------------------------------------

def _record_to_csl_json(record: dict) -> dict:
    """Convert a single literature record to CSL JSON."""
    citekey = record.get("citekey", "unknown")
    title = record.get("title", "")
    authors = record.get("authors", [])
    year = record.get("year")
    doi = record.get("doi", "")
    journal = record.get("journal", "")
    volume = record.get("volume", "")
    pages = record.get("pages", "")
    abstract = record.get("abstract", "")

    # Map authors to CSL name format
    csl_authors = []
    for author in authors:
        if "," in author:
            parts = author.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
        else:
            parts = author.strip().split()
            if len(parts) >= 2:
                family = parts[-1]
                given = " ".join(parts[:-1])
            else:
                family = parts[0] if parts else author
                given = ""
        csl_authors.append({"family": family, "given": given})

    # Determine CSL type
    csl_type = "article-journal"
    if not journal:
        csl_type = "book" if record.get("volume") else "manuscript"

    entry: dict[str, Any] = {
        "id": citekey,
        "type": csl_type,
    }

    if title:
        entry["title"] = title
    else:
        warnings.warn(f"CSL JSON: citekey '{citekey}' missing title")

    if csl_authors:
        entry["author"] = csl_authors

    if year:
        entry["issued"] = {"date-parts": [[int(year)]]}

    if journal:
        entry["container-title"] = journal
    if volume:
        entry["volume"] = volume
    if pages:
        entry["page"] = pages
    if doi:
        entry["DOI"] = doi
    if abstract:
        entry["abstract"] = abstract

    # URL from DOI
    if doi:
        from dedup import normalize_doi
        ndoi = normalize_doi(doi)
        if ndoi:
            entry["URL"] = f"https://doi.org/{ndoi}"

    return entry


def export_csl_json(project_dir: Path | None = None, output_path: Path | None = None) -> int:
    """Export catalog.jsonl to references.csl.json.

    Returns the number of entries exported.
    """
    root = project_dir or _find_project_root()
    records = read_catalog(root)

    if not records:
        print("警告: catalog.jsonl 为空，未生成任何 CSL JSON 条目")
        return 0

    csl_path = output_path or (root / "literature" / "references.csl.json")
    csl_path.parent.mkdir(parents=True, exist_ok=True)

    entries = []
    for record in records:
        citekey = record.get("citekey")
        if not citekey:
            warnings.warn(f"跳过: canonical_id={record.get('canonical_id', '?')} 缺少 citekey")
            continue
        entries.append(_record_to_csl_json(record))

    with open(csl_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"已导出 {len(entries)} 条 CSL JSON 记录到 {csl_path}")
    return len(entries)


# ---------------------------------------------------------------------------
# Citekey sync check
# ---------------------------------------------------------------------------

def _extract_bib_citekeys(path: Path) -> list[str]:
    """Extract citekeys from a BibTeX file."""
    if not path.exists():
        return []
    keys = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("@"):
                # @article{key,
                brace = line.find("{")
                comma = line.find(",", brace)
                end = comma if comma > brace else len(line)
                key = line[brace + 1:end].strip()
                keys.append(key)
    return keys


def _extract_csl_ids(path: Path) -> list[str]:
    """Extract IDs from a CSL JSON file."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [e.get("id", "") for e in data if isinstance(e, dict)]


def sync_citekeys(bib_path: Path, csl_path: Path) -> bool:
    """Check that BibTeX citekeys and CSL JSON IDs are identical sets.

    Returns True if consistent.
    """
    bib_keys = set(_extract_bib_citekeys(bib_path))
    csl_ids = set(_extract_csl_ids(csl_path))

    consistent = bib_keys == csl_ids
    if not consistent:
        only_bib = bib_keys - csl_ids
        only_csl = csl_ids - bib_keys
        if only_bib:
            print(f"仅在 .bib 中: {only_bib}")
        if only_csl:
            print(f"仅在 .csl.json 中: {only_csl}")
        return False
    return True


# ---------------------------------------------------------------------------
# Duplicate citekey detection
# ---------------------------------------------------------------------------

def find_duplicate_citekeys(bib_path: Path) -> list[str]:
    """Find duplicate citekeys in a BibTeX file."""
    keys = _extract_bib_citekeys(bib_path)
    seen = set()
    dupes = set()
    for k in keys:
        if k in seen:
            dupes.add(k)
        seen.add(k)
    return sorted(dupes)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Export references from catalog.jsonl")
    parser.add_argument("--project", help="Paper project root directory")
    parser.add_argument("--format", choices=["bib", "csl", "both"], default="both")
    parser.add_argument("--output-bib", help="Output path for .bib")
    parser.add_argument("--output-csl", help="Output path for .csl.json")
    parser.add_argument("--sync", action="store_true",
                        help="Only check citekey sync between existing files")
    args = parser.parse_args()

    project_dir = Path(args.project) if args.project else _find_project_root()

    if args.sync:
        bib = project_dir / "literature" / "references.bib"
        csl = project_dir / "literature" / "references.csl.json"
        ok = sync_citekeys(bib, csl)
        print("citekey 一致" if ok else "citekey 不一致!")
        return 0 if ok else 1

    bib_count = 0
    csl_count = 0

    if args.format in ("bib", "both"):
        bib_out = Path(args.output_bib) if args.output_bib else None
        bib_count = export_bib(project_dir, bib_out)

    if args.format in ("csl", "both"):
        csl_out = Path(args.output_csl) if args.output_csl else None
        csl_count = export_csl_json(project_dir, csl_out)

    if args.format == "both":
        # Auto-sync check after export
        bib_p = project_dir / "literature" / "references.bib"
        csl_p = project_dir / "literature" / "references.csl.json"
        if bib_p.exists() and csl_p.exists():
            ok = sync_citekeys(bib_p, csl_p)
            if not ok:
                return 1

    return 0 if (bib_count >= 0 and csl_count >= 0) else 1


if __name__ == "__main__":
    sys.exit(main())
