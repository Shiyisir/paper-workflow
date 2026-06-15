"""Test validate_manuscript.py."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import validate_manuscript as vm


def _write_md(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestValidateStructure:
    def test_heading_skip_detected(self, tmp_path):
        md = _write_md("# H1\n\n### H3 (skipped H2)\n", tmp_path / "test.md")
        result = vm.validate_structure(md)
        assert len(result["errors"]) > 0
        assert any("跳跃" in e for e in result["errors"])

    def test_no_heading_skip(self, tmp_path):
        md = _write_md("# H1\n\n## H2\n\n### H3\n", tmp_path / "test.md")
        result = vm.validate_structure(md)
        assert all("跳跃" not in e for e in result["errors"])

    def test_cite_needed_detected(self, tmp_path):
        md = _write_md("# Intro\n\nA claim [CITE NEEDED].\n", tmp_path / "test.md")
        result = vm.validate_structure(md)
        assert any("CITE NEEDED" in w for w in result["warnings"])

    def test_missing_file(self, tmp_path):
        result = vm.validate_structure(tmp_path / "nonexistent.md")
        assert result["errors"][0].startswith("文件不存在")

    def test_duplicate_figure_numbers(self, tmp_path):
        md = _write_md("# Test\n\n图1 test\n\n图1 duplicate\n", tmp_path / "test.md")
        result = vm.validate_structure(md)
        assert any("重复" in e for e in result["errors"])


class TestValidateFormulas:
    def test_unclosed_display_math(self, tmp_path):
        md = _write_md("$$\nx = 1\n", tmp_path / "test.md")  # Only opening $$
        result = vm.validate_formulas(md)
        assert any("不成对" in e for e in result["errors"])

    def test_unicode_subscript_warning(self, tmp_path):
        md = _write_md("H₁₂O test\n", tmp_path / "test.md")
        result = vm.validate_formulas(md)
        assert any("Unicode 下标" in w for w in result["warnings"])

    def test_tag_in_docx_profile(self, tmp_path):
        md = _write_md("$$\\tag{1} x=1 $$\n", tmp_path / "test.md")
        result = vm.validate_formulas(md, profile="thesis-cn")
        assert any("tag" in w.lower() for w in result["warnings"])

    def test_tag_ok_in_latex_profile(self, tmp_path):
        md = _write_md("$$\\tag{1} x=1 $$\n", tmp_path / "test.md")
        result = vm.validate_formulas(md, profile="journal-latex")
        # latex profile should not warn about \tag
        assert not any("tag" in w.lower() for w in result["warnings"])


class TestValidateAttachments:
    def test_missing_image(self, tmp_path):
        md = _write_md("![](figures/missing.png)\n", tmp_path / "test.md")
        result = vm.validate_attachments(md, tmp_path)
        assert any("缺失" in e for e in result["errors"])

    def test_existing_image_ok(self, tmp_path):
        (tmp_path / "figures").mkdir()
        (tmp_path / "figures" / "exists.png").write_text("fake png")
        md = _write_md("![](figures/exists.png)\n", tmp_path / "test.md")
        result = vm.validate_attachments(md, tmp_path)
        assert len(result["errors"]) == 0

    def test_svg_is_warning(self, tmp_path):
        (tmp_path / "figures").mkdir()
        (tmp_path / "figures" / "chart.svg").write_text("<svg></svg>")
        md = _write_md("![](figures/chart.svg)\n", tmp_path / "test.md")
        result = vm.validate_attachments(md, tmp_path)
        assert any("SVG" in w for w in result["warnings"])
        # SVG existence should not be an error
        assert len(result["errors"]) == 0

    def test_web_url_skipped(self, tmp_path):
        md = _write_md("![](https://example.com/img.png)\n", tmp_path / "test.md")
        result = vm.validate_attachments(md, tmp_path)
        assert len(result["errors"]) == 0


class TestValidateManuscript:
    def test_integrated_result(self, tmp_path):
        md = _write_md("# Title\n\n[CITE NEEDED] claim\n\n$$x=1$$\n", tmp_path / "test.md")
        result = vm.validate_manuscript(md)
        assert "errors" in result
        assert "warnings" in result
        assert "summary" in result
        assert isinstance(result["has_errors"], bool)

    def test_clean_manuscript(self, tmp_path):
        md = _write_md("# Title\n\n## Section\n\nText [@wang2024].\n\n$$\nx = 1\n$$\n",
                        tmp_path / "test.md")
        result = vm.validate_manuscript(md)
        assert result["has_errors"] is False
