#!/usr/bin/env python3
"""Search log — append-only JSONL for tracking literature search history.

Stored at .paper-workflow/search-log.jsonl.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


def _find_project_root() -> Path:
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


def get_search_log_path(project_root: Path | None = None) -> Path:
    root = project_root or _find_project_root()
    return root / ".paper-workflow" / "search-log.jsonl"


def log_search(
    query: str,
    source: str,
    count: int = 0,
    filters: dict | None = None,
    search_mode: str = "standard",
    notes: str = "",
    project_root: Path | None = None,
) -> dict:
    """Append a search record to search-log.jsonl.

    Args:
        query: The search query string.
        source: Database or skill name (cnki, scopus, pubmed, crossref, arxiv, ...).
        count: Number of results returned.
        filters: Applied filters (year range, language, etc.).
        search_mode: quick, standard, or systematic.
        notes: Free-text notes about the search.
        project_root: Paper project root (auto-detected).

    Returns:
        The logged entry dict.
    """
    path = get_search_log_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "source": source,
        "count": count,
        "filters": filters or {},
        "search_mode": search_mode,
        "notes": notes,
    }

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def get_search_history(project_root: Path | None = None) -> list[dict]:
    """Read all search log entries."""
    path = get_search_log_path(project_root)
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def get_search_count(project_root: Path | None = None) -> int:
    """Return total number of search sessions."""
    return len(get_search_history(project_root))
