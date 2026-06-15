"""Test validate_citations.py."""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import validate_citations as vc


class TestExtractCitations:
    def test_simple_bracket(self):
        text = "Some claim [@wang2024Rocky]."
        path = _write_md(text)
        keys = vc.extract_markdown_citations(path)
        assert "wang2024Rocky" in keys

    def test_multiple_in_bracket(self):
        text = "Multiple [@wang2024Rocky; @zhang2023DL]."
        path = _write_md(text)
        keys = vc.extract_markdown_citations(path)
        assert "wang2024Rocky" in keys
        assert "zhang2023DL" in keys

    def test_suppress_author(self):
        text = "As shown [-@wang2024Rocky]."
        path = _write_md(text)
        keys = vc.extract_markdown_citations(path)
        assert "wang2024Rocky" in keys

    def test_standalone_at(self):
        text = "As @wang2024Rocky demonstrates."
        path = _write_md(text)
        keys = vc.extract_markdown_citations(path)
        assert "wang2024Rocky" in keys

    def test_no_citations(self):
        text = "No citations here."
        path = _write_md(text)
        keys = vc.extract_markdown_citations(path)
        assert keys == set()

    def test_missing_file(self):
        assert vc.extract_markdown_citations(Path("/nonexistent.md")) == set()


class TestFindCiteNeeded:
    def test_finds_cite_needed(self):
        text = "This claim needs support [CITE NEEDED]."
        path = _write_md(text)
        results = vc.find_cite_needed(path)
        assert len(results) == 1
        assert results[0]["line"] == 1

    def test_case_insensitive(self):
        text = "Also [cite needed] and [Cite Needed]."
        path = _write_md(text)
        results = vc.find_cite_needed(path)
        assert len(results) == 2

    def test_no_cite_needed(self):
        text = "All properly cited [@wang2024Rocky]."
        path = _write_md(text)
        results = vc.find_cite_needed(path)
        assert results == []

    def test_line_number_accurate(self):
        text = "Line 1\nLine 2\nLine 3 [CITE NEEDED]\nLine 4"
        path = _write_md(text)
        results = vc.find_cite_needed(path)
        assert results[0]["line"] == 3

    def test_returns_context(self):
        text = "The impact of desertification is severe [CITE NEEDED] according to studies."
        path = _write_md(text)
        results = vc.find_cite_needed(path)
        assert "context" in results[0]
        assert "CITE NEEDED" in results[0]["context"]


class TestCitekeyConsistency:
    def test_all_consistent(self, tmp_path):
        md = _write_md("Test [@wang2024Rocky].", tmp_path / "test.md")
        bib = _write_bib("@article{wang2024Rocky,\n  title = {Test},\n}", tmp_path / "refs.bib")
        result = vc.check_citekey_consistency(md, bib)
        assert result["missing_in_bib"] == []
        assert result["unused_in_text"] == []

    def test_missing_in_bib(self, tmp_path):
        md = _write_md("Test [@missingKey].", tmp_path / "test.md")
        bib = _write_bib("@article{wang2024Rocky,\n  title = {Test},\n}", tmp_path / "refs.bib")
        result = vc.check_citekey_consistency(md, bib)
        assert "missingKey" in result["missing_in_bib"]

    def test_unused_in_text(self, tmp_path):
        md = _write_md("Test [@wang2024Rocky].", tmp_path / "test.md")
        bib = _write_bib(
            "@article{wang2024Rocky,\n  title = {A},\n}\n\n"
            "@article{unusedKey,\n  title = {B},\n}",
            tmp_path / "refs.bib"
        )
        result = vc.check_citekey_consistency(md, bib)
        assert "unusedKey" in result["unused_in_text"]

    def test_duplicate_citekeys(self, tmp_path):
        bib = _write_bib(
            "@article{dup,\n  title = {A},\n}\n\n"
            "@article{dup,\n  title = {B},\n}",
            tmp_path / "refs.bib"
        )
        dupes = vc.check_duplicate_citekeys_wrapper(bib)
        assert "dup" in dupes


class TestCrossCheck:
    def test_manuscript_citekeys_in_claim_map(self, tmp_path):
        md = _write_md("Test [@wang2024Rocky].", tmp_path / "test.md")
        cm = _write_claim_map(
            [{"claim_id": "C001", "supporting_citekeys": "wang2024Rocky"}],
            tmp_path / "claims.csv",
        )
        result = vc.cross_check_citations(md, cm)
        assert result["in_manuscript_not_in_claim_map"] == []

    def test_evidence_gap_detected(self, tmp_path):
        md = _write_md("Test [@wang2024Rocky; @missingEvidence].", tmp_path / "test.md")
        cm = _write_claim_map(
            [{"claim_id": "C001", "supporting_citekeys": "wang2024Rocky"}],
            tmp_path / "claims.csv",
        )
        result = vc.cross_check_citations(md, cm)
        assert "missingEvidence" in result["in_manuscript_not_in_claim_map"]


# --- Helpers ---

def _write_md(text: str, path: Path | None = None) -> Path:
    if path is None:
        import tempfile
        tmp = Path(tempfile.mkdtemp()) / "test.md"
    else:
        tmp = path
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(text, encoding="utf-8")
    return tmp


def _write_bib(content: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_claim_map(rows: list[dict], path: Path) -> Path:
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ["claim_id", "section", "claim", "supporting_citekeys", "strength", "verified", "notes"]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            full = {h: row.get(h, "") for h in header}
            writer.writerow(full)
    return path
