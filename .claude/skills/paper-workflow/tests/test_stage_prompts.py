"""Test stage_prompts.py: handoff prompt template rendering."""
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import stage_prompts as sp


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "test-project"
    root.mkdir(parents=True)
    (root / ".paper-workflow").mkdir()
    (root / "manuscript").mkdir()
    (root / "literature").mkdir()
    (root / "materials" / "requirements").mkdir(parents=True)
    (root / "materials" / "templates").mkdir(parents=True)
    (root / "materials" / "examples").mkdir(parents=True)
    (root / "materials" / "notes").mkdir(parents=True)
    return root


def _base_state():
    return {"project_id": "test-paper", "paper_type": "course_paper",
            "research_type": "experimental", "discipline": "computer_science", "language": "zh"}


def _base_config():
    return {"project_id": "test-paper", "paper_type": "course_paper",
            "research_type": "experimental", "discipline": "computer_science", "language": "zh",
            "search_mode": "standard"}


class TestRenderHandoffPrompt:
    def test_outline_prompt_contains_nature_writing(self, tmp_path):
        root = _make_project(tmp_path)
        prompt = sp.render_handoff_prompt("outline", root, _base_state(), _base_config())
        assert "nature-writing" in prompt
        assert "outline" in prompt.lower()

    def test_deep_reading_prompt_contains_nature_reader(self, tmp_path):
        root = _make_project(tmp_path)
        prompt = sp.render_handoff_prompt("deep_reading", root, _base_state(), _base_config())
        assert "nature-reader" in prompt

    def test_literature_search_zh_routes_to_cnki(self, tmp_path):
        root = _make_project(tmp_path)
        state = _base_state()
        config = _base_config()
        prompt = sp.render_handoff_prompt("literature_search", root, state, config)
        assert "cnki-search" in prompt

    def test_literature_search_en_routes_to_nature(self, tmp_path):
        root = _make_project(tmp_path)
        state = dict(_base_state())
        config = dict(_base_config())
        state["language"] = "en"
        config["language"] = "en"
        prompt = sp.render_handoff_prompt("literature_search", root, state, config)
        assert "nature-academic-search" in prompt

    def test_writing_prompt_contains_manuscript_path(self, tmp_path):
        root = _make_project(tmp_path)
        prompt = sp.render_handoff_prompt("writing", root, _base_state(), _base_config())
        assert "manuscript/outline.md" in prompt or "writing" in prompt

    def test_all_6_skill_handoff_stages_generate(self, tmp_path):
        root = _make_project(tmp_path)
        stages = ["literature_search", "deep_reading", "outline", "writing", "polishing", "charts_and_tables"]
        for sid in stages:
            prompt = sp.render_handoff_prompt(sid, root, _base_state(), _base_config())
            assert len(prompt) > 50, f"Prompt for {sid} too short: {len(prompt)} chars"

    def test_polishing_prompt_generates(self, tmp_path):
        root = _make_project(tmp_path)
        prompt = sp.render_handoff_prompt("polishing", root, _base_state(), _base_config())
        assert "nature-polishing" in prompt

    def test_charts_prompt_generates(self, tmp_path):
        root = _make_project(tmp_path)
        prompt = sp.render_handoff_prompt("charts_and_tables", root, _base_state(), _base_config())
        assert "nature-figure" in prompt


class TestMaterialsSummary:
    def test_materials_in_prompt(self, tmp_path):
        root = _make_project(tmp_path)
        (root / "materials" / "requirements" / "course-requirements.md").write_text("# Req", encoding="utf-8")
        (root / "materials" / "templates" / "reference.docx").write_text("fake", encoding="utf-8")
        prompt = sp.render_handoff_prompt("outline", root, _base_state(), _base_config())
        assert "course-requirements.md" in prompt
        assert "reference.docx" in prompt

    def test_missing_materials_not_blocked(self, tmp_path):
        root = _make_project(tmp_path)
        # Delete materials
        import shutil
        mats = root / "materials"
        if mats.exists():
            shutil.rmtree(mats)
        prompt = sp.render_handoff_prompt("outline", root, _base_state(), _base_config())
        assert len(prompt) > 50

    def test_empty_materials_gives_placeholder(self, tmp_path):
        root = _make_project(tmp_path)
        prompt = sp.render_handoff_prompt("outline", root, _base_state(), _base_config())
        assert "暂无项目补充材料" in prompt or len(prompt) > 50


class TestTemplateVariables:
    def test_returns_core_variables(self, tmp_path):
        root = _make_project(tmp_path)
        vars = sp.get_template_variables("outline", root, _base_state(), _base_config())
        assert vars["topic"] == "test-paper"
        assert vars["discipline"] == "computer_science"
        assert vars["language"] == "zh"
        assert "nature-writing" in vars["skill"]

    def test_missing_variables_fallback(self, tmp_path):
        root = _make_project(tmp_path)
        # Minimal state/config with missing fields
        prompt = sp.render_handoff_prompt("outline", root, {}, {})
        assert len(prompt) > 20  # fallback prompt works

    def test_catalog_summary_when_empty(self, tmp_path):
        root = _make_project(tmp_path)
        vars = sp.get_template_variables("deep_reading", root, _base_state(), _base_config())
        assert "为空" in vars["catalog_summary"] or "0 条" in vars["catalog_summary"]
