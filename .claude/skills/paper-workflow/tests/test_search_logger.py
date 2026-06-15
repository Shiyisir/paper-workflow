"""Test search_logger.py."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import search_logger as sl


class TestSearchLogger:
    def _setup_project(self, tmp_path: Path) -> Path:
        root = tmp_path / "test-project"
        root.mkdir(parents=True)
        (root / ".paper-workflow").mkdir()
        return root

    def test_log_search(self, tmp_path):
        root = self._setup_project(tmp_path)
        entry = sl.log_search(
            "rocky desertification",
            source="scopus",
            count=42,
            filters={"year": "2020-2024"},
            project_root=root,
        )
        assert entry["query"] == "rocky desertification"
        assert entry["source"] == "scopus"
        assert entry["count"] == 42
        assert "timestamp" in entry

    def test_get_search_history(self, tmp_path):
        root = self._setup_project(tmp_path)
        sl.log_search("query 1", "cnki", project_root=root)
        sl.log_search("query 2", "pubmed", project_root=root)

        history = sl.get_search_history(root)
        assert len(history) == 2
        assert history[0]["query"] == "query 1"
        assert history[1]["query"] == "query 2"

    def test_get_search_count(self, tmp_path):
        root = self._setup_project(tmp_path)
        assert sl.get_search_count(root) == 0
        sl.log_search("test", "crossref", project_root=root)
        assert sl.get_search_count(root) == 1

    def test_empty_history(self, tmp_path):
        root = self._setup_project(tmp_path)
        history = sl.get_search_history(root)
        assert history == []

    def test_file_is_created(self, tmp_path):
        root = self._setup_project(tmp_path)
        sl.log_search("test", "arxiv", project_root=root)
        log_path = root / ".paper-workflow" / "search-log.jsonl"
        assert log_path.exists()

    def test_log_includes_optional_fields(self, tmp_path):
        root = self._setup_project(tmp_path)
        entry = sl.log_search(
            "transformer architecture",
            source="crossref",
            search_mode="standard",
            notes="Round 1: core keyword search",
            project_root=root,
        )
        assert entry["search_mode"] == "standard"
        assert "Round 1" in entry["notes"]
