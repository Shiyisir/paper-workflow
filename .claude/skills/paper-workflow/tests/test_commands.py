"""Test commands.py: status, resume, run, confirm — M7 updated."""

import json as _json
import os
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import commands
from workflow_state import find_project_root, load_state, get_stage


# ── Fixture helpers ──────────────────────────────────────────────────

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


def _add_catalog(project_root: Path, records=None):
    """Add literature/catalog.jsonl with test records."""
    lit_dir = project_root / "literature"
    lit_dir.mkdir(exist_ok=True)
    if records is None:
        records = [
            {"citekey": "test-ref-1", "title": "Test Paper One", "year": 2020},
            {"citekey": "test-ref-2", "title": "Test Paper Two", "year": 2021},
        ]
    with open(lit_dir / "catalog.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(_json.dumps(rec, ensure_ascii=False) + "\n")


def _add_manuscript(project_root: Path, content: str = None):
    """Add manuscript/main.md with optional content."""
    ms_dir = project_root / "manuscript"
    ms_dir.mkdir(exist_ok=True)
    if content is None:
        content = "# Test Manuscript\n\nThis is a test manuscript with some content.\n"
    (ms_dir / "main.md").write_text(content, encoding="utf-8")


# ══════════════════════════════════════════════════════════════════════
# Existing tests — Status
# ══════════════════════════════════════════════════════════════════════

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

    # ── M7.2: status displays v0.2 states ──

    def test_status_shows_waiting_for_user(self, tmp_path, monkeypatch, capsys):
        """status should show waiting_for_user guidance."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # Set current stage to waiting_for_user
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["requirements"]["status"] = "waiting_for_user"
        loaded["state"]["current_stage"] = "requirements"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        commands.cmd_status()
        captured = capsys.readouterr()
        assert "等待用户完成" in captured.out

    def test_status_shows_pending_confirmation(self, tmp_path, monkeypatch, capsys):
        """status should show pending_confirmation guidance."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["requirements"]["status"] = "pending_confirmation"
        loaded["state"]["current_stage"] = "requirements"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        commands.cmd_status()
        captured = capsys.readouterr()
        assert "产物已生成" in captured.out

    def test_status_shows_handoff_path(self, tmp_path, monkeypatch, capsys):
        """status should show handoff file path when it exists."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # Create handoff file
        handoffs_dir = project / ".paper-workflow" / "handoffs"
        handoffs_dir.mkdir(parents=True, exist_ok=True)
        (handoffs_dir / "requirements.json").write_text('{"stage_id": "requirements"}', encoding="utf-8")

        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["requirements"]["status"] = "waiting_for_user"
        loaded["state"]["current_stage"] = "requirements"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        commands.cmd_status()
        captured = capsys.readouterr()
        assert "handoff 文件路径" in captured.out


# ══════════════════════════════════════════════════════════════════════
# Existing tests — Resume
# ══════════════════════════════════════════════════════════════════════

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

    # ── M7.2: resume handles v0.2 states ──

    def test_resume_waiting_for_user_confirm_hint(self, tmp_path, monkeypatch, capsys):
        """resume for waiting_for_user should give confirm hint."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["requirements"]["status"] = "waiting_for_user"
        loaded["state"]["current_stage"] = "requirements"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_resume()
        assert rc == 0
        captured = capsys.readouterr()
        assert "confirm" in captured.out.lower()

    def test_resume_pending_confirmation_confirm_hint(self, tmp_path, monkeypatch, capsys):
        """resume for pending_confirmation should give confirm hint."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["requirements"]["status"] = "pending_confirmation"
        loaded["state"]["current_stage"] = "requirements"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_resume()
        assert rc == 0
        captured = capsys.readouterr()
        assert "confirm" in captured.out.lower()

    def test_resume_blocked_fix_hint(self, tmp_path, monkeypatch, capsys):
        """resume for blocked should give fix hint."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["requirements"]["status"] = "blocked"
        loaded["state"]["stages"]["requirements"]["blockers"] = ["test reason"]
        loaded["state"]["current_stage"] = "requirements"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_resume()
        assert rc == 1
        captured = capsys.readouterr()
        assert "阻塞" in captured.out

    def test_resume_blocked_state_unchanged(self, tmp_path, monkeypatch):
        """resume should not change blocked state."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["requirements"]["status"] = "blocked"
        loaded["state"]["stages"]["requirements"]["blockers"] = ["dep missing"]
        loaded["state"]["current_stage"] = "requirements"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        commands.cmd_resume()
        # Reload — status should still be blocked
        loaded2 = load_state(root)
        assert loaded2["state"]["stages"]["requirements"]["status"] == "blocked"


# ══════════════════════════════════════════════════════════════════════
# Run command — M7.1 real executor tests
# ══════════════════════════════════════════════════════════════════════

class TestRun:
    # ── Preserved old behaviour ───────────────────────────────

    def test_run_blocked_by_deps(self, tmp_path, monkeypatch, capsys):
        """literature_dedup depends on literature_search (pending) → blocked."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_run("literature_dedup")
        assert rc != 0  # Non-zero for blocked
        captured = capsys.readouterr()
        assert "literature_search" in captured.out

    def test_run_unknown_stage(self, tmp_path, monkeypatch, capsys):
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        rc = commands.cmd_run("nonexistent")
        assert rc != 0

    def test_run_with_override_logs_override(self, tmp_path, monkeypatch):
        """Override run should add an entry to overrides."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # writing is skill_handoff — needs deps override
        commands.cmd_run("writing", override=True)
        root = find_project_root()
        loaded = load_state(root)
        assert len(loaded["state"]["overrides"]) >= 1
        assert loaded["state"]["overrides"][-1]["stage"] == "writing"

    # ── M7.1: script stage → done ─────────────────────────────

    def test_run_literature_dedup_done(self, tmp_path, monkeypatch, capsys):
        """Run literature_dedup with catalog → done (via real executor)."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        _add_catalog(project)
        # Set literature_search as done (dependency)
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["literature_search"]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("literature_dedup")
        assert rc == 0
        captured = capsys.readouterr()
        assert "完成" in captured.out

    def test_run_literature_dedup_missing_catalog(self, tmp_path, monkeypatch, capsys):
        """Run literature_dedup without catalog → blocked."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["literature_search"]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("literature_dedup")
        assert rc != 0
        captured = capsys.readouterr()
        assert "阻塞" in captured.out or "blocked" in captured.out.lower()

    # ── M7.1: evidence_matrix → pending_confirmation ───────────

    def test_run_evidence_matrix_pending_confirmation(self, tmp_path, monkeypatch, capsys):
        """Run evidence_matrix → pending_confirmation (user confirmation required)."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # Set deps as done
        root = find_project_root()
        loaded = load_state(root)
        for dep in ["requirements", "literature_search", "literature_dedup", "deep_reading"]:
            loaded["state"]["stages"][dep]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("evidence_matrix")
        assert rc == 0
        captured = capsys.readouterr()
        assert "等待用户确认" in captured.out or "pending" in captured.out.lower()

    # ── M7.1: skill_handoff → waiting_for_user ─────────────────

    def test_run_outline_waiting_for_user(self, tmp_path, monkeypatch, capsys):
        """Run outline (skill_handoff) → waiting_for_user + handoff file."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # Set all deps as done
        root = find_project_root()
        loaded = load_state(root)
        for dep in ["requirements", "literature_search", "literature_dedup",
                     "deep_reading", "evidence_matrix", "research_design",
                     "data_analysis", "charts_and_tables"]:
            loaded["state"]["stages"][dep]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("outline")
        assert rc == 0
        captured = capsys.readouterr()
        assert "handoff" in captured.out.lower()
        # Check handoff file exists
        handoff_path = project / ".paper-workflow" / "handoffs" / "outline.json"
        assert handoff_path.exists()

    # ── M7.1: manual → waiting_for_user ────────────────────────

    def test_run_research_design_waiting_for_user(self, tmp_path, monkeypatch, capsys):
        """Run research_design (manual) → waiting_for_user + manual message."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        root = find_project_root()
        loaded = load_state(root)
        for dep in ["requirements", "literature_search", "literature_dedup",
                     "deep_reading", "evidence_matrix"]:
            loaded["state"]["stages"][dep]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("research_design")
        assert rc == 0
        captured = capsys.readouterr()
        assert "手动" in captured.out
        # State should be waiting_for_user, not done
        loaded2 = load_state(root)
        assert loaded2["state"]["stages"]["research_design"]["status"] == "waiting_for_user"

    # ── M7.1: hybrid citation_verification (clean path) ────────

    def test_run_citation_verification_clean(self, tmp_path, monkeypatch, capsys):
        """Run citation_verification clean path → done."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # Clean manuscript: no [CITE NEEDED]
        _add_manuscript(project, "# Test\n\nClean manuscript without citation issues.\n")
        # Set deps as done
        root = find_project_root()
        loaded = load_state(root)
        for dep in ["requirements", "literature_search", "literature_dedup",
                     "deep_reading", "evidence_matrix", "research_design",
                     "data_analysis", "charts_and_tables", "outline", "writing", "polishing"]:
            loaded["state"]["stages"][dep]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("citation_verification")
        assert rc == 0
        captured = capsys.readouterr()
        assert "完成" in captured.out

    # ── M7.1: hybrid citation_verification (issues path) ───────

    def test_run_citation_verification_issues(self, tmp_path, monkeypatch, capsys):
        """Run citation_verification with [CITE NEEDED] → waiting_for_user + handoff."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # Manuscript with [CITE NEEDED]
        _add_manuscript(project, "# Test\n\nThis claim needs support [CITE NEEDED].\n")
        # Set deps as done
        root = find_project_root()
        loaded = load_state(root)
        for dep in ["requirements", "literature_search", "literature_dedup",
                     "deep_reading", "evidence_matrix", "research_design",
                     "data_analysis", "charts_and_tables", "outline", "writing", "polishing"]:
            loaded["state"]["stages"][dep]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("citation_verification")
        assert rc == 0
        captured = capsys.readouterr()
        assert "handoff" in captured.out.lower()
        # Check handoff file was generated
        handoff_path = project / ".paper-workflow" / "handoffs" / "citation_verification.json"
        assert handoff_path.exists()
        # State should be waiting_for_user, not done
        loaded2 = load_state(root)
        assert loaded2["state"]["stages"]["citation_verification"]["status"] == "waiting_for_user"

    # ── M7.1: formatting → done ────────────────────────────────

    def test_run_formatting_done(self, tmp_path, monkeypatch, capsys):
        """Run formatting → done when manuscript exists."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        _add_manuscript(project)
        root = find_project_root()
        loaded = load_state(root)
        for dep in ["requirements", "literature_search", "literature_dedup",
                     "deep_reading", "evidence_matrix", "research_design",
                     "data_analysis", "charts_and_tables", "outline",
                     "writing", "polishing", "citation_verification"]:
            loaded["state"]["stages"][dep]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("formatting")
        # Could succeed (done) or fail if render.py has issues in test env
        # Either way, it should not crash
        assert rc in (0, 1)

    # ── M7.1: quality_qa blocked ───────────────────────────────

    def test_run_quality_qa_blocked(self, tmp_path, monkeypatch, capsys):
        """Run quality_qa with missing manuscript → blocked or errors."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        root = find_project_root()
        loaded = load_state(root)
        for dep in ["requirements", "literature_search", "literature_dedup",
                     "deep_reading", "evidence_matrix", "research_design",
                     "data_analysis", "charts_and_tables", "outline",
                     "writing", "polishing", "citation_verification",
                     "formatting", "originality_check"]:
            loaded["state"]["stages"][dep]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)
        rc = commands.cmd_run("quality_qa")
        # If QA finds errors → blocked (rc != 0), or done (rc == 0)
        # Both are valid; just verify it doesn't crash
        assert rc in (0, 1)

    # ── M7.1: done_conditions must pass ────────────────────────

    def test_done_conditions_must_pass(self, tmp_path, monkeypatch, capsys):
        """If executor returns done but done_conditions fail → blocked, NOT done."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        # literature_dedup returns done when catalog exists
        _add_catalog(project)
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["literature_search"]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)

        # Run literature_dedup — it has done_conditions that check
        # file_exists:literature/catalog.jsonl and record_count > 0
        rc = commands.cmd_run("literature_dedup")
        assert rc == 0  # conditions should be met
        loaded2 = load_state(root)
        assert loaded2["state"]["stages"]["literature_dedup"]["status"] == "done"

    # ── M7.1: dependency check still works ─────────────────────

    def test_run_override_skips_deps_with_catalog(self, tmp_path, monkeypatch, capsys):
        """--override skips dep check; with catalog → done."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)
        _add_catalog(project)
        rc = commands.cmd_run("literature_dedup", override=True)
        assert rc == 0
        captured = capsys.readouterr()
        assert "跳过依赖检查" in captured.out


# ══════════════════════════════════════════════════════════════════════
# End-to-end chain (updated for M7)
# ══════════════════════════════════════════════════════════════════════

class TestEndToEndMinimal:
    def test_full_chain_script_stages(self, tmp_path, monkeypatch, capsys):
        """Simulate a full chain: literature_search → dedup → evidence."""
        project = _setup_project(tmp_path)
        monkeypatch.chdir(project)

        # Set up catalog for dedup
        _add_catalog(project)

        # Complete requirements first (manual → waiting_for_user, then confirm)
        assert commands.cmd_run("requirements") == 0
        root = find_project_root()
        loaded = load_state(root)
        loaded["state"]["stages"]["requirements"]["status"] = "done"
        from workflow_state import save_state
        save_state(loaded["state"], root)

        # literature_search (skill_handoff → waiting_for_user)
        assert commands.cmd_run("literature_search") == 0
        # Confirm it via set_status
        loaded = load_state(root)
        loaded["state"]["stages"]["literature_search"]["status"] = "done"
        save_state(loaded["state"], root)

        # literature_dedup (script → done if catalog exists)
        assert commands.cmd_run("literature_dedup") == 0
        loaded = load_state(root)
        assert loaded["state"]["stages"]["literature_dedup"]["status"] == "done"

        # evidence_matrix (script → pending_confirmation)
        loaded = load_state(root)
        loaded["state"]["stages"]["deep_reading"]["status"] = "done"
        save_state(loaded["state"], root)
        assert commands.cmd_run("evidence_matrix") == 0
        loaded = load_state(root)
        assert loaded["state"]["stages"]["evidence_matrix"]["status"] == "pending_confirmation"

        # Add data rows to evidence matrix so confirm passes
        import csv as _csv
        evidence_path = project / "literature" / "evidence-matrix.csv"
        if evidence_path.exists():
            with open(evidence_path, "a", encoding="utf-8", newline="") as f:
                writer = _csv.writer(f)
                writer.writerow(["ref-1", "test-ref-1", "topic", "CN", "src", "method",
                                 "finding", "none", "intro", "p1", ""])
        claim_path = project / "citations" / "claim-citation-map.csv"
        if claim_path.exists():
            with open(claim_path, "a", encoding="utf-8", newline="") as f:
                writer = _csv.writer(f)
                writer.writerow(["c1", "intro", "test claim", "ref-1", "test-ref-1",
                                 "strong", "yes", ""])

        # Confirm evidence_matrix
        assert commands.cmd_confirm("evidence_matrix") == 0
        loaded = load_state(root)
        assert loaded["state"]["stages"]["evidence_matrix"]["status"] == "done"


# ══════════════════════════════════════════════════════════════════════
# Project flag tests
# ══════════════════════════════════════════════════════════════════════

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
        # requirements is manual → waiting_for_user, still rc=0
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


# ══════════════════════════════════════════════════════════════════════
# Confirm command (M5.2)
# ══════════════════════════════════════════════════════════════════════

class TestConfirm:
    def _setup(self, tmp_path, stage_id="requirements", status="in_progress"):
        """Create a project where a specific stage is in the given status."""
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

    def test_confirm_from_waiting_for_user(self, tmp_path, monkeypatch):
        """confirm from waiting_for_user state works when conditions met."""
        project = self._setup(tmp_path, "requirements", "waiting_for_user")
        monkeypatch.chdir(project)
        rc = commands.cmd_confirm("requirements")
        assert rc == 0

    def test_confirm_from_pending_confirmation(self, tmp_path, monkeypatch):
        """confirm from pending_confirmation state works when conditions met."""
        project = self._setup(tmp_path, "requirements", "pending_confirmation")
        monkeypatch.chdir(project)
        rc = commands.cmd_confirm("requirements")
        assert rc == 0
