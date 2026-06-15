"""Test commands.py: status, resume, run."""

import os
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import commands
from workflow_state import find_project_root, load_state, get_stage


def _setup_project(tmp_path: Path, paper_type: str = "course_paper") -> Path:
    """Create a minimal paper project for command testing."""
    project_root = tmp_path / "test-project"
    project_root.mkdir(parents=True)
    pw_dir = project_root / ".paper-workflow"
    pw_dir.mkdir()

    # Write config
    config = {
        "project_id": "test-001",
        "paper_type": paper_type,
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "search_mode": "quick",
        "search_capabilities": {},
    }
    with open(pw_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)

    # Write state
    from init_project import STAGE_IDS, DEPENDENCY_GRAPH
    stages = {}
    for sid in STAGE_IDS:
        stages[sid] = {
            "status": "pending",
            "depends_on": DEPENDENCY_GRAPH.get(sid, []),
            "started_at": None,
            "completed_at": None,
            "qa_status": "pending",
            "qa_report": None,
            "artifacts": [],
            "blockers": [],
        }
    stages["requirements"]["status"] = "in_progress"

    state = {
        "schema_version": 1,
        "project_id": "test-001",
        "paper_type": paper_type,
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "current_stage": "requirements",
        "stages": stages,
        "overrides": [],
    }
    with open(pw_dir / "state.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True)

    return project_root


class TestStatus:
    def test_status_returns_zero(self, tmp_path, monkeypatch, capsys):
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_status()
        assert rc == 0

    def test_status_shows_project_info(self, tmp_path, monkeypatch, capsys):
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        commands.cmd_status()
        captured = capsys.readouterr()
        assert "test-001" in captured.out
        assert "requirements" in captured.out

    def test_status_verbose(self, tmp_path, monkeypatch, capsys):
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        commands.cmd_status(verbose=True)
        captured = capsys.readouterr()
        assert "全部阶段" in captured.out

    def test_status_no_project(self, tmp_path, monkeypatch, capsys):
        """Should return non-zero when not in a project directory."""
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        rc = commands.cmd_status()
        assert rc != 0


class TestResume:
    def test_resume_in_progress(self, tmp_path, monkeypatch, capsys):
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_resume()
        assert rc == 0
        captured = capsys.readouterr()
        assert "requirements" in captured.out

    def test_resume_no_project(self, tmp_path, monkeypatch, capsys):
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        rc = commands.cmd_resume()
        assert rc != 0


class TestRun:
    def test_run_requirements_succeeds(self, tmp_path, monkeypatch, capsys):
        """requirements has no deps → should succeed."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_run("requirements")
        assert rc == 0
        captured = capsys.readouterr()
        assert "完成" in captured.out

    def test_run_blocked_by_deps(self, tmp_path, monkeypatch, capsys):
        """literature_dedup depends on literature_search (pending) → blocked."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_run("literature_dedup")
        assert rc != 0  # Non-zero for blocked
        captured = capsys.readouterr()
        assert "literature_search" in captured.out

    def test_run_override_skips_deps(self, tmp_path, monkeypatch, capsys):
        """--override should skip dep check."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_run("literature_dedup", override=True)
        assert rc == 0
        captured = capsys.readouterr()
        assert "跳过依赖检查" in captured.out

    def test_run_unknown_stage(self, tmp_path, monkeypatch, capsys):
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_run("nonexistent")
        assert rc != 0

    def test_run_already_done(self, tmp_path, monkeypatch, capsys):
        """Running an already-done stage should be a no-op."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # First run requirements
        commands.cmd_run("requirements")
        # Second run should say it's already done
        rc = commands.cmd_run("requirements")
        assert rc == 0
        captured = capsys.readouterr()
        assert "已完成" in captured.out

    def test_run_persists_state(self, tmp_path, monkeypatch):
        """After run, state.yaml should reflect the new status."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        commands.cmd_run("requirements")
        # Reload and check
        root = find_project_root()
        loaded = load_state(root)
        assert loaded["state"]["stages"]["requirements"]["status"] == "done"

    def test_run_with_override_logs_override(self, tmp_path, monkeypatch):
        """Override run should add an entry to overrides."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        commands.cmd_run("writing", override=True)
        root = find_project_root()
        loaded = load_state(root)
        assert len(loaded["state"]["overrides"]) >= 1
        assert loaded["state"]["overrides"][-1]["stage"] == "writing"


class TestEndToEndMinimal:
    def test_full_chain_requirements_to_writing(self, tmp_path, monkeypatch, capsys):
        """Simulate a minimal workflow execution chain."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)

        # Complete requirements
        assert commands.cmd_run("requirements") == 0
        # Complete via override (chain covers research_design → data_analysis → charts_and_tables)
        assert commands.cmd_run("literature_search", override=True) == 0
        assert commands.cmd_run("literature_dedup", override=True) == 0
        assert commands.cmd_run("deep_reading", override=True) == 0
        assert commands.cmd_run("evidence_matrix", override=True) == 0
        assert commands.cmd_run("research_design", override=True) == 0
        assert commands.cmd_run("data_analysis", override=True) == 0
        assert commands.cmd_run("charts_and_tables", override=True) == 0
        assert commands.cmd_run("outline", override=True) == 0
        # Now writing should work without override (all deps met via override chain)
        assert commands.cmd_run("writing") == 0

        # Check state
        root = find_project_root()
        loaded = load_state(root)
        assert loaded["state"]["stages"]["writing"]["status"] == "done"

        # Status should reflect progress
        commands.cmd_status()
        captured = capsys.readouterr()
        assert "writing (done)" in captured.out
