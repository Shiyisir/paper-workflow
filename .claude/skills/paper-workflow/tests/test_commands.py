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


class TestProjectFlag:
    """Test --project flag across all commands."""

    def test_status_with_project_flag(self, tmp_path, monkeypatch, capsys):
        """status --project <path> works from outside project directory."""
        project = _setup_project(tmp_path)
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        rc = commands.cmd_status(project=str(project))
        assert rc == 0
        captured = capsys.readouterr()
        assert "test-001" in captured.out

    def test_status_with_project_flag_rejects_bad_path(self, tmp_path, monkeypatch):
        """--project with invalid path returns non-zero."""
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        rc = commands.cmd_status(project=str(empty))
        assert rc != 0

    def test_resume_with_project_flag(self, tmp_path, monkeypatch, capsys):
        """resume --project <path> works from outside project directory."""
        project = _setup_project(tmp_path)
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        rc = commands.cmd_resume(project=str(project))
        assert rc == 0
        captured = capsys.readouterr()
        assert "requirements" in captured.out

    def test_run_with_project_flag(self, tmp_path, monkeypatch):
        """run --project <path> works from outside project directory."""
        project = _setup_project(tmp_path)
        empty = tmp_path / "empty"
        empty.mkdir()
        monkeypatch.chdir(empty)
        rc = commands.cmd_run("requirements", project=str(project))
        assert rc == 0

    def test_auto_discovery_from_subdir(self, tmp_path, monkeypatch, capsys):
        """status auto-discovers project from subdirectory."""
        project = _setup_project(tmp_path)
        subdir = project / "manuscript"
        subdir.mkdir()
        monkeypatch.chdir(subdir)
        rc = commands.cmd_status()
        assert rc == 0
        captured = capsys.readouterr()
        assert "test-001" in captured.out

    def test_auto_discovery_fails_outside_project(self, tmp_path, monkeypatch):
        """status fails gracefully when no project found."""
        empty = tmp_path / "no-project"
        empty.mkdir(parents=True)
        monkeypatch.chdir(empty)
        rc = commands.cmd_status()
        assert rc != 0


# ===== M5.2: Confirm command =====

class TestConfirm:
    def _setup(self, tmp_path, stage_id="requirements", status="in_progress"):
        """Create a project where a specific stage is in_progress."""
        import yaml as _yaml
        project = tmp_path / "test-project"
        project.mkdir(parents=True)
        pw_dir = project / ".paper-workflow"
        pw_dir.mkdir()

        # Build stages with one stage in the given status
        from init_project import STAGE_IDS, DEPENDENCY_GRAPH
        stages = {}
        for sid in STAGE_IDS:
            s_status = status if sid == stage_id else "pending"
            stages[sid] = {
                "status": s_status,
                "depends_on": DEPENDENCY_GRAPH.get(sid, []),
                "started_at": None, "completed_at": None,
                "qa_status": "pending", "qa_report": None,
                "artifacts": [], "blockers": [],
            }

        state = {
            "schema_version": 1, "project_id": "test-001",
            "paper_type": "course_paper", "research_type": "review",
            "discipline": "computer_science", "language": "zh",
            "target_journal": None, "current_stage": stage_id,
            "stages": stages, "overrides": [],
        }
        with open(pw_dir / "state.yaml", "w", encoding="utf-8") as f:
            _yaml.dump(state, f, allow_unicode=True)
        config = {
            "project_id": "test-001", "paper_type": "course_paper",
            "search_mode": "standard",
        }
        with open(pw_dir / "config.yaml", "w", encoding="utf-8") as f:
            _yaml.dump(config, f, allow_unicode=True)

        # Create minimal done_condition artifacts for requirements
        (project / "manuscript").mkdir(exist_ok=True)
        (project / "manuscript" / "notes.md").write_text("# Notes", encoding="utf-8")

        return project

    def test_confirm_with_met_conditions(self, tmp_path, monkeypatch):
        """requirements has done_condition: file_exists:manuscript/notes.md"""
        project = self._setup(tmp_path, "requirements", "in_progress")
        monkeypatch.chdir(project)
        rc = commands.cmd_confirm("requirements")
        assert rc == 0

    def test_confirm_with_unmet_conditions(self, tmp_path, monkeypatch):
        """formatting needs outputs/latest/ which doesn't exist."""
        project = self._setup(tmp_path, "formatting", "in_progress")
        monkeypatch.chdir(project)
        rc = commands.cmd_confirm("formatting")
        assert rc != 0  # blocked, conditions not met

    def test_confirm_override_forced(self, tmp_path, monkeypatch):
        """--override forces done even with unmet conditions."""
        project = self._setup(tmp_path, "formatting", "in_progress")
        monkeypatch.chdir(project)
        rc = commands.cmd_confirm("formatting", override=True)
        assert rc == 0  # override succeeds

    def test_confirm_already_done(self, tmp_path, monkeypatch, capsys):
        """Confirming an already-done stage returns cleanly."""
        project = self._setup(tmp_path, "requirements", "done")
        monkeypatch.chdir(project)
        rc = commands.cmd_confirm("requirements")
        assert rc == 0
        captured = capsys.readouterr()
        assert "已完成" in captured.out

    def test_confirm_unknown_stage(self, tmp_path, monkeypatch):
        project = self._setup(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_confirm("nonexistent")
        assert rc != 0

    def test_confirm_override_logs_record(self, tmp_path, monkeypatch):
        """Override logs to state overrides."""
        project = self._setup(tmp_path, "formatting", "in_progress")
        monkeypatch.chdir(project)
        commands.cmd_confirm("formatting", override=True)
        # Check state has override record
        from workflow_state import load_state
        loaded = load_state()
        overrides = loaded["state"].get("overrides", [])
        assert len(overrides) >= 1
        assert overrides[-1]["stage"] == "formatting"

    def test_confirm_skill_handoff_checks_stage_done(self, tmp_path, monkeypatch, capsys):
        """skill_handoff confirm should check stage_done, not handoff_done."""
        project = self._setup(tmp_path, "outline", "waiting_for_user")
        monkeypatch.chdir(project)
        rc = commands.cmd_confirm("outline")
        # outline needs manuscript/outline.md — should fail
        assert rc != 0
        captured = capsys.readouterr()
        assert "stage_done" in captured.out.lower() or "未满足条件" in captured.out

    def test_run_still_uses_stub(self, tmp_path, monkeypatch):
        """verify that run <stage> still uses the old _execute_stage stub (M7 not done)."""
        project = self._setup(tmp_path, "requirements", "in_progress")
        monkeypatch.chdir(project)
        import commands as cmds
        # run should still print stub message
        old_run = getattr(cmds, 'cmd_run')
        # We just verify the _execute_stage function still exists as stub
        assert callable(cmds._execute_stage)
        # and that it returns a dict with executed=False (stub behavior)
        r = cmds._execute_stage("literature_dedup")
        assert r.get("executed") is False
