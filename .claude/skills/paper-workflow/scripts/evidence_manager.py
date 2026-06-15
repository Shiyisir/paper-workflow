#!/usr/bin/env python3
"""Evidence matrix and claim-citation map management.

Files:
    literature/evidence-matrix.csv
    citations/claim-citation-map.csv
"""

import csv
import os
import tempfile
from pathlib import Path

# --- Constants ---

EVIDENCE_HEADER = [
    "ref_id", "citekey", "topic", "region", "data_source",
    "method", "key_finding", "limitation", "usable_sections",
    "page_ref", "notes",
]

CLAIM_HEADER = [
    "claim_id", "section", "claim", "supporting_refs",
    "supporting_citekeys", "strength", "verified", "notes",
]

VALID_STRENGTHS = {"strong", "medium", "weak"}
VALID_VERIFIED = {"yes", "pending", "no"}


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
# Evidence Matrix
# ---------------------------------------------------------------------------

def get_evidence_path(project_dir: Path | None = None) -> Path:
    root = project_dir or _find_project_root()
    return root / "literature" / "evidence-matrix.csv"


def init_evidence_matrix(project_dir: Path | None = None) -> Path:
    """Create evidence-matrix.csv with header if it doesn't exist."""
    path = get_evidence_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _atomic_write_csv(path, [], EVIDENCE_HEADER)
    return path


def add_evidence_entry(entry: dict, project_dir: Path | None = None) -> None:
    """Append one evidence entry. Writes atomically via read→append→replace."""
    path = get_evidence_path(project_dir)
    init_evidence_matrix(project_dir)
    rows = _read_csv(path)
    # Build ordered row
    row = {col: entry.get(col, "") for col in EVIDENCE_HEADER}
    rows.append(row)
    _atomic_write_csv(path, rows, EVIDENCE_HEADER)


def get_evidence_for_section(section: str, project_dir: Path | None = None) -> list[dict]:
    """Get evidence entries whose usable_sections contains `section`."""
    path = get_evidence_path(project_dir)
    if not path.exists():
        return []
    rows = _read_csv(path)
    section_lower = section.strip().lower()
    result = []
    for row in rows:
        usable = row.get("usable_sections", "").lower()
        sections = {s.strip() for s in usable.split(";")}
        if section_lower in sections:
            result.append(row)
    return result


def get_evidence_by_citekey(citekey: str, project_dir: Path | None = None) -> list[dict]:
    """Get evidence entries for a specific citekey."""
    path = get_evidence_path(project_dir)
    if not path.exists():
        return []
    rows = _read_csv(path)
    return [r for r in rows if r.get("citekey", "").strip() == citekey]


# ---------------------------------------------------------------------------
# Claim-Citation Map
# ---------------------------------------------------------------------------

def get_claim_map_path(project_dir: Path | None = None) -> Path:
    root = project_dir or _find_project_root()
    return root / "citations" / "claim-citation-map.csv"


def init_claim_map(project_dir: Path | None = None) -> Path:
    """Create claim-citation-map.csv with header if it doesn't exist."""
    path = get_claim_map_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        _atomic_write_csv(path, [], CLAIM_HEADER)
    return path


def add_claim(claim: dict, project_dir: Path | None = None) -> str:
    """Append a claim. Returns the assigned claim_id (C001, C002, ...)."""
    path = get_claim_map_path(project_dir)
    init_claim_map(project_dir)
    rows = _read_csv(path)

    # Validate strength
    strength = claim.get("strength", "medium")
    if strength not in VALID_STRENGTHS:
        raise ValueError(f"Invalid strength '{strength}'. Must be one of {VALID_STRENGTHS}")

    # Validate verified
    verified = claim.get("verified", "pending")
    if verified not in VALID_VERIFIED:
        raise ValueError(f"Invalid verified '{verified}'. Must be one of {VALID_VERIFIED}")

    # Auto-generate claim_id
    max_n = 0
    for row in rows:
        cid = row.get("claim_id", "")
        if cid.startswith("C") and cid[1:].isdigit():
            max_n = max(max_n, int(cid[1:]))
    claim_id = f"C{max_n + 1:03d}"

    row = {col: claim.get(col, "") for col in CLAIM_HEADER}
    row["claim_id"] = claim_id
    row["strength"] = strength
    row["verified"] = verified
    rows.append(row)

    _atomic_write_csv(path, rows, CLAIM_HEADER)
    return claim_id


def get_claims_by_section(section: str, project_dir: Path | None = None) -> list[dict]:
    """Get claims for a specific section."""
    path = get_claim_map_path(project_dir)
    if not path.exists():
        return []
    rows = _read_csv(path)
    target = section.strip().lower()
    return [r for r in rows if r.get("section", "").strip().lower() == target]


def get_claims_by_citekey(citekey: str, project_dir: Path | None = None) -> list[dict]:
    """Get all claims that reference a specific citekey."""
    path = get_claim_map_path(project_dir)
    if not path.exists():
        return []
    rows = _read_csv(path)
    result = []
    for row in rows:
        sc = row.get("supporting_citekeys", "")
        keys = {k.strip() for k in sc.split(";") if k.strip()}
        if citekey in keys:
            result.append(row)
    return result


def get_all_claims(project_dir: Path | None = None) -> list[dict]:
    """Get all claims as a list of dicts."""
    path = get_claim_map_path(project_dir)
    if not path.exists():
        return []
    return _read_csv(path)


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> list[dict]:
    """Read CSV and return list of dicts."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _atomic_write_csv(path: Path, rows: list[dict], header: list[str]) -> None:
    """Write CSV atomically: temp file + rename."""
    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=".csv", prefix=".tmp-", dir=str(path.parent)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            for row in rows:
                # Only write columns from the header
                clean = {col: row.get(col, "") for col in header}
                writer.writerow(clean)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
