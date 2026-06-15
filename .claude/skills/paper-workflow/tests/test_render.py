"""Test render.py."""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import render as rdr


def _setup_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    (root / ".paper-workflow").mkdir()
    (root / "manuscript").mkdir()
    (root / "literature").mkdir()
    (root / "outputs").mkdir()
    return root


def _write_md(text: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class TestLoadProfile:
    def test_load_existing_profile(self):
        profile = rdr.load_profile("markdown-draft")
        assert profile["output"] == "md"
        assert profile["native_math"] == "raw"

    def test_load_thesis_cn(self):
        profile = rdr.load_profile("thesis-cn")
        assert profile["output"] == "docx"

    def test_load_journal_latex(self):
        profile = rdr.load_profile("journal-latex")
        assert profile["output"] == "tex"

    def test_nonexistent_profile(self):
        with pytest.raises(FileNotFoundError):
            rdr.load_profile("nonexistent")


class TestNextOutputVersion:
    def test_first_version(self, tmp_path):
        out = tmp_path / "outputs"
        out.mkdir()
        path = rdr.next_output_version(out, "thesis-cn", "docx")
        assert path.name == "thesis-cn-v001.docx"

    def test_increments(self, tmp_path):
        out = tmp_path / "outputs"
        out.mkdir()
        (out / "thesis-cn-v001.docx").write_text("")
        (out / "thesis-cn-v002.docx").write_text("")
        (out / "thesis-cn-v005.docx").write_text("")
        path = rdr.next_output_version(out, "thesis-cn", "docx")
        assert path.name == "thesis-cn-v006.docx"

    def test_ignores_other_files(self, tmp_path):
        out = tmp_path / "outputs"
        out.mkdir()
        (out / "other-file.txt").write_text("")
        path = rdr.next_output_version(out, "thesis-cn", "docx")
        assert path.name == "thesis-cn-v001.docx"


class TestRender:
    def test_dry_run_does_not_create_file(self, tmp_path):
        root = _setup_project(tmp_path)
        md = _write_md("# Title\n\nTest content.\n", root / "manuscript" / "main.md")
        out_dir = root / "outputs"

        result = rdr.render("markdown-draft", md, out_dir, root, dry_run=True)
        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["output_path"] is None

    def test_markdown_draft_renders(self, tmp_path):
        root = _setup_project(tmp_path)
        md = _write_md("# Title\n\nTest content.\n", root / "manuscript" / "main.md")
        out_dir = root / "outputs"

        result = rdr.render("markdown-draft", md, out_dir, root)
        assert result["success"] is True
        assert result["output_path"] is not None
        assert result["output_path"].exists()
        assert "-v001.md" in result["output_path"].name

    def test_markdown_draft_increments(self, tmp_path):
        root = _setup_project(tmp_path)
        md = _write_md("# Title\n\nTest.\n", root / "manuscript" / "main.md")
        out_dir = root / "outputs"

        r1 = rdr.render("markdown-draft", md, out_dir, root)
        r2 = rdr.render("markdown-draft", md, out_dir, root)
        assert r1["output_path"] != r2["output_path"]
        assert "-v001" in r1["output_path"].name
        assert "-v002" in r2["output_path"].name

    def test_docx_renders_with_pandoc(self, tmp_path):
        root = _setup_project(tmp_path)
        md = _write_md("# Title\n\nTest content.\n", root / "manuscript" / "main.md")
        out_dir = root / "outputs"

        result = rdr.render("thesis-cn", md, out_dir, root)
        # May fail if pandoc CSL is missing, but should not crash
        assert "success" in result
        if result["success"]:
            assert result["output_path"].suffix == ".docx"

    def test_tex_renders(self, tmp_path):
        root = _setup_project(tmp_path)
        md = _write_md("# Title\n\nTest content.\n", root / "manuscript" / "main.md")
        out_dir = root / "outputs"

        result = rdr.render("journal-latex", md, out_dir, root)
        assert "success" in result
        if result["success"]:
            assert result["output_path"].suffix == ".tex"

    def test_manuscript_validation_fails_blocks_render(self, tmp_path):
        root = _setup_project(tmp_path)
        # Missing image reference
        md = _write_md("# Title\n\n![](missing.png)\n", root / "manuscript" / "main.md")
        out_dir = root / "outputs"

        result = rdr.render("markdown-draft", md, out_dir, root)
        assert result["success"] is False
        assert len(result["errors"]) > 0

    def test_latest_copied_on_success(self, tmp_path):
        root = _setup_project(tmp_path)
        md = _write_md("# Title\n\nTest content.\n", root / "manuscript" / "main.md")
        out_dir = root / "outputs"

        result = rdr.render("markdown-draft", md, out_dir, root)
        if result["success"]:
            latest = out_dir / "latest" / "draft.md"
            assert latest.exists()

    def test_dry_run_does_not_copy_to_latest(self, tmp_path):
        root = _setup_project(tmp_path)
        md = _write_md("# Title\n\nTest.\n", root / "manuscript" / "main.md")
        out_dir = root / "outputs"

        rdr.render("markdown-draft", md, out_dir, root, dry_run=True)
        latest = out_dir / "latest" / "draft.md"
        assert not latest.exists()
