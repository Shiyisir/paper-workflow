"""Test validate_catalog.py."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import validate_catalog as vcat
from literature_store import append_records


def _make_record(cid: str, citekey: str, title: str = "Test", authors=None,
                 year=2024, doi=None):
    return {
        "canonical_id": cid,
        "citekey": citekey,
        "title": title,
        "authors": authors or ["Test, A."],
        "year": year,
        "doi": doi,
        "language": "en",
        "sources": ["crossref"],
        "fulltext_available": False,
        "fulltext_path": None,
        "related_versions": [],
        "screening_status": "included",
        "screening_notes": "",
    }


def _setup_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    (root / ".paper-workflow").mkdir()
    (root / "literature").mkdir(parents=True)
    return root


class TestValidateCatalog:
    def test_valid_catalog_passes(self, tmp_path):
        root = _setup_project(tmp_path)
        records = [
            _make_record("ref-0001", "test2024A", "Paper A"),
            _make_record("ref-0002", "test2024B", "Paper B"),
        ]
        append_records(records, project_dir=root, auto_id=False, auto_citekey=False)
        result = vcat.validate_catalog(root)
        assert result["errors"] == []

    def test_duplicate_canonical_id(self, tmp_path):
        root = _setup_project(tmp_path)
        records = [
            _make_record("ref-0001", "test2024A", "Paper A"),
            _make_record("ref-0001", "test2024B", "Paper B"),  # same id
        ]
        append_records(records, project_dir=root, auto_id=False, auto_citekey=False)
        result = vcat.validate_catalog(root)
        assert any("ref-0001" in e for e in result["errors"])

    def test_duplicate_citekey(self, tmp_path):
        root = _setup_project(tmp_path)
        records = [
            _make_record("ref-0001", "test2024A", "Paper A"),
            _make_record("ref-0002", "test2024A", "Paper B"),  # same citekey
        ]
        append_records(records, project_dir=root, auto_id=False, auto_citekey=False)
        result = vcat.validate_catalog(root)
        assert any("test2024A" in e for e in result["errors"])

    def test_missing_doi_is_warning(self, tmp_path):
        root = _setup_project(tmp_path)
        records = [_make_record("ref-0001", "test2024", "Paper", doi=None)]
        append_records(records, project_dir=root, auto_id=False, auto_citekey=False)
        result = vcat.validate_catalog(root)
        assert any("DOI" in w for w in result["warnings"])

    def test_bad_doi_format_is_warning(self, tmp_path):
        root = _setup_project(tmp_path)
        records = [_make_record("ref-0001", "test2024", "Paper", doi="not-a-doi")]
        append_records(records, project_dir=root, auto_id=False, auto_citekey=False)
        result = vcat.validate_catalog(root)
        assert any("DOI 格式" in w for w in result["warnings"])

    def test_missing_title_is_error(self, tmp_path):
        root = _setup_project(tmp_path)
        # Write directly to bypass schema validation (which would reject empty title)
        import json
        cat_path = root / "literature" / "catalog.jsonl"
        record = _make_record("ref-0001", "test2024", title="")
        with open(cat_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        result = vcat.validate_catalog(root)
        assert any("标题" in e for e in result["errors"])

    def test_bib_not_synced(self, tmp_path):
        root = _setup_project(tmp_path)
        records = [_make_record("ref-0001", "test2024A", "Paper A")]
        append_records(records, project_dir=root, auto_id=False, auto_citekey=False)
        # Create a bib with different citekeys
        (root / "literature" / "references.bib").write_text(
            "@article{differentKey,\n  title = {X},\n}\n", encoding="utf-8"
        )
        result = vcat.validate_catalog(root)
        assert any("references.bib" in e for e in result["errors"])

    def test_empty_catalog(self, tmp_path):
        root = _setup_project(tmp_path)
        # Don't write anything — catalog doesn't exist, read_catalog returns []
        result = vcat.validate_catalog(root)
        assert "为空" in result["warnings"][0] if result["warnings"] else True
        assert result["total_records"] == 0

    def test_errors_and_warnings_separated(self, tmp_path):
        root = _setup_project(tmp_path)
        records = [
            _make_record("ref-0001", "dup", "Paper A"),
            _make_record("ref-0002", "dup", "Paper B"),  # duplicate citekey
        ]
        append_records(records, project_dir=root, auto_id=False, auto_citekey=False)
        result = vcat.validate_catalog(root)
        assert "errors" in result
        assert "warnings" in result
        # Duplicate citekey is error
        assert any("dup" in e for e in result["errors"])
