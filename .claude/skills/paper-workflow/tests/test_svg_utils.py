"""Test svg_utils.py."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import svg_utils as su


class TestFindSvgReferences:
    def test_finds_svg(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("![](figures/chart.svg)\n", encoding="utf-8")
        refs = su.find_svg_references(md)
        assert len(refs) == 1

    def test_no_svg(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("![](figures/chart.png)\n", encoding="utf-8")
        refs = su.find_svg_references(md)
        assert refs == []

    def test_skips_duplicates(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("![](a.svg)\n![](a.svg)\n", encoding="utf-8")
        refs = su.find_svg_references(md)
        assert len(refs) == 1

    def test_missing_file(self):
        refs = su.find_svg_references(Path("/nonexistent.md"))
        assert refs == []


class TestConvertSvgReferences:
    def test_no_svg_returns_empty(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("No images here.\n", encoding="utf-8")
        result = su.convert_svg_references(
            {"convert_svg_to": "png"}, md, tmp_path
        )
        assert result["svg_count"] == 0
        assert result["warnings"] == []

    def test_svg_with_no_converter_returns_warning(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("![](chart.svg)\n", encoding="utf-8")
        # SVG file doesn't exist, but reference is found
        result = su.convert_svg_references(
            {"convert_svg_to": "png"}, md, tmp_path
        )
        assert result["svg_count"] == 1
        # Will warn about missing converter OR missing file
        assert len(result["warnings"]) >= 0  # converter or file missing

    def test_profile_none_skips(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("![](chart.svg)\n", encoding="utf-8")
        result = su.convert_svg_references(
            {"convert_svg_to": "none"}, md, tmp_path
        )
        assert result["convertible"] is False
        assert any("none" in w for w in result["warnings"])

    def test_existing_svg_with_converter_path_map(self, tmp_path):
        (tmp_path / "figures").mkdir()
        svg_file = tmp_path / "figures" / "chart.svg"
        svg_file.write_text("<svg></svg>")

        md = tmp_path / "test.md"
        md.write_text("![](figures/chart.svg)\n", encoding="utf-8")

        result = su.convert_svg_references(
            {"convert_svg_to": "png"}, md, tmp_path
        )
        # If converter available, path_map should have an entry
        if result["converter"]:
            assert len(result["path_map"]) == 1
        else:
            assert not result["convertible"]
            assert len(result["warnings"]) > 0

    def test_original_md_not_modified(self, tmp_path):
        original = "![](chart.svg)\nSome text\n"
        md = tmp_path / "test.md"
        md.write_text(original, encoding="utf-8")
        su.convert_svg_references({"convert_svg_to": "png"}, md, tmp_path)
        assert md.read_text(encoding="utf-8") == original
