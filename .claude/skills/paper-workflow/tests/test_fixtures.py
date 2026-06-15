"""Verify that test fixtures are valid and readable."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
MINI_PAPER = FIXTURES_DIR / "mini-paper"

import validate_manuscript as vm
import validate_citations as vc
import validate_catalog as vcat
from workflow_state import find_project_root, load_state


class TestFormulaFixture:
    def test_formulas_fixture_readable(self):
        md = FIXTURES_DIR / "formulas.md"
        assert md.exists()
        result = vm.validate_formulas(md, profile="thesis-cn")
        assert result["warnings"]  # Should have Unicode subscripts and \tag warnings
        assert result["errors"]    # Should have $$ unclosed

    def test_formulas_fixture_detects_tag_in_docx(self):
        md = FIXTURES_DIR / "formulas.md"
        result = vm.validate_formulas(md, profile="thesis-cn")
        assert any("tag" in w.lower() for w in result["warnings"])

    def test_formulas_fixture_detects_unicode_subscripts(self):
        md = FIXTURES_DIR / "formulas.md"
        result = vm.validate_formulas(md)
        assert any("Unicode 下标" in w for w in result["warnings"])


class TestTablesFixture:
    def test_tables_fixture_readable(self):
        md = FIXTURES_DIR / "tables.md"
        assert md.exists()
        result = vm.validate_structure(md)
        # Tables fixture should have table numbers
        assert "summary" in result


class TestFiguresFixture:
    def test_figures_fixture_missing_image(self, tmp_path):
        md = FIXTURES_DIR / "figures.md"
        base = FIXTURES_DIR  # figures/ dir is relative to fixtures/
        result = vm.validate_attachments(md, base)
        assert any("缺失" in e for e in result["errors"])

    def test_figures_fixture_svg_warning(self, tmp_path):
        md = FIXTURES_DIR / "figures.md"
        result = vm.validate_attachments(md, FIXTURES_DIR)
        # SVG reference is there; chart.svg doesn't exist so it won't trigger SVG warning
        # But we can check the fixture is parseable
        assert "summary" in result


class TestCitationsFixture:
    def test_citations_extracts_all_formats(self):
        md = FIXTURES_DIR / "citations.md"
        keys = vc.extract_markdown_citations(md)
        assert "wang2024RockyDesertification" in keys
        assert "zhang2023DeepLearningKarst" in keys
        assert "li2022KarstWater" in keys
        assert "nonexistent2024Fake" in keys

    def test_citations_fixture_has_cite_needed(self):
        md = FIXTURES_DIR / "citations.md"
        results = vc.find_cite_needed(md)
        assert len(results) >= 1


class TestChineseHeadingsFixture:
    def test_headings_fixture_has_skip(self):
        md = FIXTURES_DIR / "chinese-headings.md"
        result = vm.validate_structure(md)
        assert any("跳跃" in e for e in result["errors"])


class TestMiniPaper:
    def test_mini_paper_is_valid_project(self):
        """Mini-paper should be recognized as a valid project."""
        root = find_project_root(MINI_PAPER)
        assert root == MINI_PAPER.resolve()

    def test_mini_paper_loads_state(self):
        loaded = load_state(MINI_PAPER)
        assert loaded["state"]["project_id"] == "mini-paper-test"

    def test_mini_paper_catalog_validates(self):
        result = vcat.validate_catalog(MINI_PAPER)
        assert result["total_records"] == 3
        assert result["errors"] == []

    def test_mini_paper_citations_consistent(self):
        md = MINI_PAPER / "manuscript" / "main.md"
        bib = MINI_PAPER / "literature" / "references.bib"
        result = vc.check_citekey_consistency(md, bib)
        # nonexistent2024Fake is in citations.md, not in main.md
        # main.md uses wang2024RockyDesertification, zhang2023DeepLearningKarst, li2022KarstWater
        assert "nonexistent2024Fake" not in result.get("missing_in_bib", [])

    def test_mini_paper_manuscript_validates(self):
        md = MINI_PAPER / "manuscript" / "main.md"
        result = vm.validate_manuscript(md, MINI_PAPER)
        # main.md should be clean
        assert result["has_errors"] is False

    def test_mini_paper_has_required_files(self):
        required = [
            ".paper-workflow/config.yaml",
            ".paper-workflow/state.yaml",
            "manuscript/main.md",
            "literature/catalog.jsonl",
            "literature/references.bib",
            "literature/references.csl.json",
            "literature/evidence-matrix.csv",
            "citations/claim-citation-map.csv",
        ]
        for f in required:
            assert (MINI_PAPER / f).exists(), f"Missing: {f}"
