#!/usr/bin/env python3
"""Literature record store — CRUD for catalog.jsonl.

All paths are relative to the paper project root (cwd or found via .paper-workflow/).
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import jsonschema

# Schema loaded lazily
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "literature-record.schema.json"
_schema_cache: dict | None = None


def _load_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        with open(_SCHEMA_PATH, encoding="utf-8") as f:
            _schema_cache = json.load(f)
    return _schema_cache


def _find_project_dir() -> Path:
    """Find project root by walking up for .paper-workflow/."""
    current = Path.cwd().resolve()
    for _ in range(10):
        if (current / ".paper-workflow").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise FileNotFoundError(
        "找不到 .paper-workflow/ 目录。请在论文项目根目录下运行。"
    )


def get_catalog_path(project_dir: Path | None = None) -> Path:
    root = project_dir or _find_project_dir()
    return root / "literature" / "catalog.jsonl"


# ---------------------------------------------------------------------------
# citekey generation
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "to", "for",
    "with", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "can", "shall",
    "this", "that", "these", "those", "it", "its",
    "not", "no", "nor", "but", "from", "by", "at",
    "into", "through", "during", "before", "after",
    "above", "below", "between", "under", "over",
    "some", "any", "each", "every", "all", "both",
    "few", "more", "most", "other", "such",
    "only", "own", "same", "so", "than", "too",
    "very", "just", "about", "also",
    "using", "based", "new", "study", "analysis",
    "de", "la", "le", "les", "des", "du", "et", "en", "un", "une",
    "der", "die", "das", "und", "von",
}


def _clean_author_last_name(name: str) -> str:
    """Extract and clean last name from author string like 'Wang, X.' or 'Wang'."""
    if "," in name:
        last = name.split(",")[0].strip()
    else:
        parts = name.strip().split()
        last = parts[-1] if parts else name.strip()
    # Remove non-alpha chars, keep ASCII letters
    last = re.sub(r"[^a-zA-Z]", "", last)
    return last.lower()


def _pick_title_keyword(title: str, year: int) -> str:
    """Pick the most distinctive word from the title for the citekey.

    Strategy: take the first non-stop word, and if it's too short (<4 chars),
    append the next non-stop word.
    """
    # Normalize: remove punctuation, split
    words = re.findall(r"[a-zA-Z]+", title.lower())
    meaningful = [w for w in words if w not in STOP_WORDS and len(w) >= 3]

    if not meaningful:
        return f"untitled{year}"

    keyword = meaningful[0].capitalize()
    # If the first word is very short or generic, add a second
    if len(meaningful) > 1 and len(meaningful[0]) < 5:
        keyword += meaningful[1].capitalize()
    return keyword


def generate_citekey(authors: list[str], year: int, title: str) -> str:
    """Generate a stable citekey from first author + year + title keyword.

    Format: <first_author_last_name_lowercase><year><TitleKeyword>
    Example: wang2024RockyDesertification
    """
    if not authors:
        last = "anonymous"
    else:
        last = _clean_author_last_name(authors[0])
    keyword = _pick_title_keyword(title, year)
    return f"{last}{year}{keyword}"


def resolve_citekey_conflict(
    desired_key: str,
    existing_keys: set[str],
) -> str:
    """Resolve citekey conflicts by appending A, B, C, ..."""
    if desired_key not in existing_keys:
        return desired_key
    for suffix_index in range(ord("A"), ord("Z") + 1):
        candidate = f"{desired_key}{chr(suffix_index)}"
        if candidate not in existing_keys:
            return candidate
    # Exhausted A-Z, use numeric
    for i in range(1, 1000):
        candidate = f"{desired_key}{i}"
        if candidate not in existing_keys:
            return candidate
    raise ValueError(f"无法为 citekey '{desired_key}' 生成无冲突后缀")


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def read_catalog(project_dir: Path | None = None) -> list[dict]:
    """Read all records from catalog.jsonl. Returns empty list if file missing."""
    path = get_catalog_path(project_dir)
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"警告: catalog.jsonl 第 {line_num} 行解析失败: {e}",
                      file=sys.stderr)
    return records


def _get_existing_ids_and_keys(records: list[dict]) -> tuple[set[str], set[str]]:
    """Extract existing canonical_ids and citekeys from records."""
    ids = {r.get("canonical_id", "") for r in records if r.get("canonical_id")}
    keys = {r.get("citekey", "") for r in records if r.get("citekey")}
    return ids, keys


def _next_canonical_id(existing_ids: set[str]) -> str:
    """Generate the next canonical_id in ref-NNNN format."""
    max_n = 0
    for cid in existing_ids:
        m = re.match(r"^ref-(\d{4})$", cid)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"ref-{max_n + 1:04d}"


def validate_record(record: dict) -> list[str]:
    """Validate a record against literature-record.schema.json.

    Returns list of error messages (empty = valid).
    """
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in validator.iter_errors(record)]


def append_records(
    records: list[dict],
    project_dir: Path | None = None,
    auto_id: bool = True,
    auto_citekey: bool = True,
) -> int:
    """Append literature records to catalog.jsonl.

    Args:
        records: List of literature record dicts.
        project_dir: Paper project root (auto-detected if None).
        auto_id: If True, generate canonical_id for records missing it.
        auto_citekey: If True, generate citekey for records missing it.

    Returns:
        Number of records successfully appended.

    Raises:
        jsonschema.ValidationError: If any record fails schema validation.
    """
    path = get_catalog_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = read_catalog(project_dir)
    existing_ids, existing_keys = _get_existing_ids_and_keys(existing)

    appended = 0
    with open(path, "a", encoding="utf-8") as f:
        for record in records:
            # Auto-generate canonical_id first (so validation sees a complete record)
            if auto_id and not record.get("canonical_id"):
                cid = _next_canonical_id(existing_ids)
                record["canonical_id"] = cid
                existing_ids.add(cid)

            # Auto-generate citekey
            if auto_citekey and not record.get("citekey"):
                desired = generate_citekey(
                    record.get("authors", []),
                    record.get("year", 0),
                    record.get("title", ""),
                )
                resolved = resolve_citekey_conflict(desired, existing_keys)
                record["citekey"] = resolved
                existing_keys.add(resolved)

            # Validate after auto-generation
            errors = validate_record(record)
            if errors:
                msg = f"文献记录校验失败: {'; '.join(errors)}"
                raise jsonschema.ValidationError(msg)

            # Append as JSONL
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            appended += 1

    return appended


def update_record(
    canonical_id: str,
    updates: dict,
    project_dir: Path | None = None,
) -> bool:
    """Update a single record by canonical_id in place.

    Returns True if the record was found and updated.
    """
    records = read_catalog(project_dir)
    for i, r in enumerate(records):
        if r.get("canonical_id") == canonical_id:
            records[i] = {**r, **updates}
            _write_full_catalog(records, project_dir)
            return True
    return False


def get_by_doi(doi: str, project_dir: Path | None = None) -> list[dict]:
    """Find records by DOI (case-insensitive substring match)."""
    doi_lower = doi.strip().lower()
    if not doi_lower:
        return []
    records = read_catalog(project_dir)
    return [r for r in records if r.get("doi") and doi_lower in r["doi"].lower()]


def get_by_citekey(citekey: str, project_dir: Path | None = None) -> dict | None:
    """Find a record by exact citekey match."""
    records = read_catalog(project_dir)
    for r in records:
        if r.get("citekey") == citekey:
            return r
    return None


def count_records(project_dir: Path | None = None) -> int:
    """Return the total number of records in catalog.jsonl."""
    return len(read_catalog(project_dir))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _write_full_catalog(records: list[dict], project_dir: Path | None = None) -> None:
    """Overwrite the entire catalog.jsonl (used by update_record)."""
    path = get_catalog_path(project_dir)
    # Atomic write: temp file + replace
    import os
    import tempfile
    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=".jsonl", prefix=".catalog-", dir=str(path.parent)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
