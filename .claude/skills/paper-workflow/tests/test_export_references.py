"""Test export_references.py."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import export_references as er


def _setup_catalog(root: Path, records: list[dict]) -> Path:
    """Create a catalog.jsonl in the project."""
    from literature_store import append_records
    (root / "literature").mkdir(parents=True, exist_ok=True)
    (root / ".paper-workflow").mkdir(parents=True, exist_ok=True)
    append_records(records, project_dir=root)
    return root / "literature" / "catalog.jsonl"


def _make_record(cid: str, citekey: str, title: str, authors: list[str],
                 year: int, doi: str | None = None, journal: str | None = None,
                 volume: str | None = None, pages: str | None = None) -> dict:
    return {
        "canonical_id": cid,
        "citekey": citekey,
        "title": title,
        "authors": authors,
        "year": year,
        "doi": doi,
        "journal": journal,
        "volume": volume,
        "pages": pages,
        "abstract": "",
        "keywords": [],
        "language": "en",
        "sources": ["crossref"],
        "fulltext_available": False,
        "fulltext_path": None,
        "related_versions": [],
        "screening_status": "included",
        "screening_notes": "",
    }


class TestExportBib:
    def test_export_3_records(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        records = [
            _make_record("ref-0001", "wang2024Rocky", "Rocky desertification",
                         ["Wang, X.", "Li, Y."], 2024, "10.1016/ecoser.2024.1",
                         "Ecosystem Services", "68"),
            _make_record("ref-0002", "zhang2023DL", "Deep learning for karst",
                         ["Zhang, L."], 2023),
            _make_record("ref-0003", "li2022Study", "Karst water study",
                         ["Li, M.", "Chen, W."], 2022, journal="Hydrogeology Journal"),
        ]
        _setup_catalog(root, records)
        count = er.export_bib(root)
        assert count == 3

        bib_path = root / "literature" / "references.bib"
        assert bib_path.exists()
        content = bib_path.read_text(encoding="utf-8")
        assert "@article{wang2024Rocky" in content
        assert "@misc{zhang2023DL" in content
        assert "@article{li2022Study" in content

    def test_missing_doi_not_blocking(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        records = [_make_record("ref-0001", "test2024", "No DOI paper",
                                ["Test, A."], 2024)]
        _setup_catalog(root, records)
        count = er.export_bib(root)
        assert count == 1

    def test_empty_catalog(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        _setup_catalog(root, [])
        count = er.export_bib(root)
        assert count == 0


class TestExportCslJson:
    def test_export_3_records(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        records = [
            _make_record("ref-0001", "wang2024Rocky", "Rocky desertification",
                         ["Wang, X.", "Li, Y."], 2024, "10.1016/ecoser.2024.1",
                         "Ecosystem Services", "68", "101650"),
            _make_record("ref-0002", "zhang2023DL", "Deep learning",
                         ["Zhang, L."], 2023),
            _make_record("ref-0003", "li2022Study", "Karst study",
                         ["Li, M.", "Chen, W."], 2022),
        ]
        _setup_catalog(root, records)
        count = er.export_csl_json(root)
        assert count == 3

        csl_path = root / "literature" / "references.csl.json"
        assert csl_path.exists()
        data = json.loads(csl_path.read_text(encoding="utf-8"))
        assert len(data) == 3
        ids = [e["id"] for e in data]
        assert "wang2024Rocky" in ids
        assert "zhang2023DL" in ids

    def test_doi_mapped_to_url(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        records = [_make_record("ref-0001", "test2024", "Paper",
                                ["Test, A."], 2024, doi="10.1234/test")]
        _setup_catalog(root, records)
        er.export_csl_json(root)

        csl_path = root / "literature" / "references.csl.json"
        data = json.loads(csl_path.read_text(encoding="utf-8"))
        assert "URL" in data[0]
        assert "doi.org/10.1234/test" in data[0]["URL"]


class TestCitekeySync:
    def test_sync_detects_consistency(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        records = [_make_record("ref-0001", "test2024", "Paper", ["Test, A."], 2024)]
        _setup_catalog(root, records)
        er.export_bib(root)
        er.export_csl_json(root)
        assert er.sync_citekeys(
            root / "literature" / "references.bib",
            root / "literature" / "references.csl.json",
        ) is True

    def test_sync_detects_inconsistency(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        records_a = [_make_record("ref-0001", "test2024A", "Paper A", ["Test, A."], 2024)]
        records_b = [_make_record("ref-0002", "test2024B", "Paper B", ["Test, B."], 2024)]
        _setup_catalog(root, records_a)
        er.export_bib(root)
        # Replace catalog with different records for CSL export
        cat_path = root / "literature" / "catalog.jsonl"
        cat_path.unlink()
        _setup_catalog(root, records_b)
        er.export_csl_json(root)

        ok = er.sync_citekeys(
            root / "literature" / "references.bib",
            root / "literature" / "references.csl.json",
        )
        assert ok is False


class TestDuplicateCitekeys:
    def test_no_duplicates(self, tmp_path):
        root = tmp_path / "project"
        root.mkdir(parents=True)
        records = [
            _make_record("ref-0001", "a2024X", "Paper A", ["Test, A."], 2024),
            _make_record("ref-0002", "b2024Y", "Paper B", ["Test, B."], 2024),
        ]
        _setup_catalog(root, records)
        er.export_bib(root)
        dupes = er.find_duplicate_citekeys(root / "literature" / "references.bib")
        assert dupes == []

    def test_detect_duplicates(self, tmp_path):
        """If a bib file has duplicate keys, should detect."""
        root = tmp_path / "project"
        root.mkdir(parents=True)
        (root / "literature").mkdir(parents=True, exist_ok=True)
        bib_path = root / "literature" / "references.bib"
        # Write a bib with duplicate keys manually
        bib_path.write_text(
            "@article{key1,\n  title = {A},\n}\n\n"
            "@article{key1,\n  title = {B},\n}\n",
            encoding="utf-8"
        )
        dupes = er.find_duplicate_citekeys(bib_path)
        assert "key1" in dupes


class TestCLIPathResolution:
    """Test export_references CLI project directory resolution."""

    _make_record = staticmethod(_make_record)

    def test_project_flag_from_outside(self, tmp_path):
        """--project flag works from outside project directory."""
        root = tmp_path / "project"
        records = [self._make_record("ref-0001", "a2024X", "Paper A", ["Test, A."], 2024)]
        _setup_catalog(root, records)
        outside = tmp_path / "outside"
        outside.mkdir()
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(str(outside))
            count = er.export_bib(root)
            assert count == 1
            assert (root / "literature" / "references.bib").exists()
        finally:
            os.chdir(old_cwd)

    def test_no_project_and_no_flag_gives_error(self, tmp_path):
        """Outside project without --project should raise clear error."""
        empty = tmp_path / "empty"
        empty.mkdir()
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(str(empty))
            with pytest.raises(FileNotFoundError):
                er._find_project_root()
        finally:
            os.chdir(old_cwd)
