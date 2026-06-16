"""Test literature_store.py."""

import json
import sys
from pathlib import Path

import jsonschema
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import literature_store as ls


class TestCitekeyGeneration:
    def test_basic_citekey(self):
        key = ls.generate_citekey(
            ["Wang, X."], 2024,
            "Rocky desertification impacts on ecosystem services in karst regions"
        )
        assert key == "wang2024Rocky"

    def test_citekey_no_comma_author(self):
        key = ls.generate_citekey(
            ["Smith"], 2023,
            "Deep learning for image classification"
        )
        # "Deep" < 5 chars → appends "Learning" → "DeepLearning"
        assert key == "smith2023DeepLearning"

    def test_citekey_anonymous(self):
        key = ls.generate_citekey([], 2022, "Some untitled work")
        assert "anonymous" in key

    def test_citekey_stop_words_skipped(self):
        key = ls.generate_citekey(
            ["Zhang, L."], 2021,
            "The analysis of the new method for the study of ecosystems"
        )
        # "the" and "analysis" skipped (analysis is stop word), "new"→4 chars
        assert key.startswith("zhang2021")

    def test_resolve_no_conflict(self):
        result = ls.resolve_citekey_conflict("wang2024Rocky", set())
        assert result == "wang2024Rocky"

    def test_resolve_conflict_append_suffix(self):
        existing = {"wang2024Rocky"}
        result = ls.resolve_citekey_conflict("wang2024Rocky", existing)
        assert result == "wang2024RockyA"

    def test_resolve_conflict_multiple(self):
        existing = {"wang2024Rocky", "wang2024RockyA", "wang2024RockyB"}
        result = ls.resolve_citekey_conflict("wang2024Rocky", existing)
        assert result == "wang2024RockyC"


class TestCatalogCRUD:
    def _setup_project(self, tmp_path: Path) -> Path:
        """Create minimal project with catalog path."""
        root = tmp_path / "test-project"
        root.mkdir(parents=True)
        (root / ".paper-workflow").mkdir()
        (root / "literature").mkdir(parents=True)
        return root

    def _make_record(self, cid: str | None = None, citekey: str | None = None,
                     title_override: str | None = None) -> dict:
        record = {
            "title": title_override or "Test paper about machine learning",
            "authors": ["Test, Author"],
            "year": 2024,
            "doi": "10.1234/test.2024",
            "journal": "Test Journal",
            "language": "en",
            "sources": ["crossref"],
            "fulltext_available": False,
            "fulltext_path": None,
            "related_versions": [],
            "screening_status": "pending",
            "screening_notes": "",
        }
        if cid is not None:
            record["canonical_id"] = cid
        if citekey is not None:
            record["citekey"] = citekey
        return record

    def test_append_and_read(self, tmp_path):
        root = self._setup_project(tmp_path)
        records = [self._make_record(), self._make_record()]
        count = ls.append_records(records, project_dir=root)
        assert count == 2

        read_back = ls.read_catalog(root)
        assert len(read_back) == 2

    def test_auto_generates_canonical_id(self, tmp_path):
        root = self._setup_project(tmp_path)
        record = self._make_record(cid=None)  # No canonical_id
        ls.append_records([record], project_dir=root)
        read_back = ls.read_catalog(root)
        assert read_back[0]["canonical_id"] == "ref-0001"

    def test_auto_generates_citekey(self, tmp_path):
        root = self._setup_project(tmp_path)
        record = self._make_record(cid=None, citekey=None, title_override="Deep learning for NLP")
        ls.append_records([record], project_dir=root)
        read_back = ls.read_catalog(root)
        assert read_back[0]["citekey"] == "test2024DeepLearning"

    def test_canonical_id_increments(self, tmp_path):
        root = self._setup_project(tmp_path)
        for i in range(3):
            record = self._make_record(cid=None, title_override=f"Paper {i}")
            ls.append_records([record], project_dir=root)
        read_back = ls.read_catalog(root)
        ids = [r["canonical_id"] for r in read_back]
        assert ids == ["ref-0001", "ref-0002", "ref-0003"]

    def test_doi_lookup(self, tmp_path):
        root = self._setup_project(tmp_path)
        r1 = self._make_record(cid=None, citekey=None)
        r1["doi"] = "10.1016/j.ecoser.2024.101650"
        ls.append_records([r1], project_dir=root)

        results = ls.get_by_doi("10.1016/j.ecoser.2024.101650", root)
        assert len(results) == 1

    def test_doi_lookup_case_insensitive(self, tmp_path):
        root = self._setup_project(tmp_path)
        r1 = self._make_record(cid=None, citekey=None)
        r1["doi"] = "10.1016/J.ECOSER.2024.101650"
        ls.append_records([r1], project_dir=root)

        results = ls.get_by_doi("10.1016/j.ecoser.2024.101650", root)
        assert len(results) == 1

    def test_citekey_lookup(self, tmp_path):
        root = self._setup_project(tmp_path)
        r1 = self._make_record(cid="ref-0001", citekey="test2024Deep")
        ls.append_records([r1], project_dir=root, auto_id=False, auto_citekey=False)

        result = ls.get_by_citekey("test2024Deep", root)
        assert result is not None
        assert result["canonical_id"] == "ref-0001"

    def test_schema_validation_rejects_bad_record(self, tmp_path):
        root = self._setup_project(tmp_path)
        bad = {"canonical_id": "bad-format"}  # Missing required fields
        with pytest.raises(jsonschema.ValidationError):
            ls.append_records([bad], project_dir=root, auto_id=False, auto_citekey=False)

    def test_citekey_conflict_auto_resolved(self, tmp_path):
        root = self._setup_project(tmp_path)
        # Two records with same author/year/title → same citekey
        r1 = self._make_record(cid=None, citekey=None, title_override="Deep learning")
        r2 = self._make_record(cid=None, citekey=None, title_override="Deep learning")
        ls.append_records([r1, r2], project_dir=root)

        read_back = ls.read_catalog(root)
        keys = [r["citekey"] for r in read_back]
        assert keys[0] != keys[1]
        assert keys[1].startswith(keys[0])

    def test_update_record(self, tmp_path):
        root = self._setup_project(tmp_path)
        r1 = self._make_record(cid="ref-0001", citekey="test2024Paper")
        ls.append_records([r1], project_dir=root, auto_id=False, auto_citekey=False)

        updated = ls.update_record("ref-0001", {"screening_status": "included"}, root)
        assert updated is True

        read_back = ls.read_catalog(root)
        assert read_back[0]["screening_status"] == "included"

    def test_update_record_not_found(self, tmp_path):
        root = self._setup_project(tmp_path)
        updated = ls.update_record("ref-9999", {"screening_status": "included"}, root)
        assert updated is False

    def test_empty_catalog(self, tmp_path):
        root = self._setup_project(tmp_path)
        records = ls.read_catalog(root)
        assert records == []

    def test_count_records(self, tmp_path):
        root = self._setup_project(tmp_path)
        for _ in range(3):
            ls.append_records([self._make_record()], project_dir=root)
        assert ls.count_records(root) == 3
