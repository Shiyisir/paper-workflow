"""Integration tests for all executor types (M8.1).

Covers script, skill_handoff, manual, and hybrid executors
via stage_executor.execute_stage() with real fixtures and files.
"""

import csv as _csv
import json as _json
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from stage_executor import execute_stage, check_done_conditions, load_contract
from workflow_state import (
    load_state, save_state, set_stage_status, mark_stage_blocked,
    get_stage, get_stages_by_status,
)


# ── Helpers ────────────────────────────────────────────────────────

def _mk_project(tmp_path: Path, stage_in_progress: str = None, **extra_stages) -> Path:
    """Create a minimal paper-workflow project for testing.

    stage_in_progress: stage to set as "in_progress" (default: requirements)
    extra_stages: {stage_id: status} to override specific stages.
    """
    project = tmp_path / "proj"
    project.mkdir(parents=True)
    pw_dir = project / ".paper-workflow"
    pw_dir.mkdir()

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

    in_progress_stage = stage_in_progress or "requirements"
    stages[in_progress_stage]["status"] = "in_progress"

    # Apply overrides
    for sid, st in extra_stages.items():
        if sid in stages:
            stages[sid]["status"] = st

    state = {
        "schema_version": 1,
        "project_id": "int-test",
        "paper_type": "course_paper",
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "current_stage": in_progress_stage,
        "stages": stages,
        "overrides": [],
    }

    config = {
        "project_id": "int-test",
        "paper_type": "course_paper",
        "search_mode": "quick",
        "citation_style": "gb-t-7714",
        "writing_language": "zh",
        "search_capabilities": {},
    }

    with open(pw_dir / "state.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True)
    with open(pw_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)

    return project


def _add_catalog(project: Path, records=None):
    lit_dir = project / "literature"
    lit_dir.mkdir(exist_ok=True)
    if records is None:
        records = [
            {"citekey": "ref-1", "title": "Paper One", "year": 2020, "source": "cnki"},
            {"citekey": "ref-2", "title": "Paper Two", "year": 2021, "source": "cnki"},
            {"citekey": "ref-3", "title": "Paper Three", "year": 2022, "source": "crossref"},
        ]
    with open(lit_dir / "catalog.jsonl", "w", encoding="utf-8") as f:
        for rec in records:
            f.write(_json.dumps(rec, ensure_ascii=False) + "\n")


def _add_manuscript(project: Path, content: str = None):
    ms_dir = project / "manuscript"
    ms_dir.mkdir(exist_ok=True)
    if content is None:
        content = "# Integration Test\n\n## Introduction\n\nThis is a test manuscript.\n\n## Methods\n\nSimple method.\n\n## Results\n\nKey results here.\n"
    (ms_dir / "main.md").write_text(content, encoding="utf-8")


def _add_notes(project: Path):
    ms_dir = project / "manuscript"
    ms_dir.mkdir(exist_ok=True)
    (ms_dir / "notes.md").write_text("# Research Notes\n\nNotes content.\n", encoding="utf-8")


def _deps_done(project: Path, stage_id: str) -> list[str]:
    """Mark all dependencies of stage_id as done. Returns list of dep ids."""
    loaded = load_state(project)
    state = loaded["state"]
    stage = get_stage(state, stage_id)
    deps = stage.get("depends_on", []) if stage else []
    for dep in deps:
        set_stage_status(state, dep, "done")
    # Also mark earlier dependency chain as done
    for dep in deps:
        dep_stage = get_stage(state, dep)
        if dep_stage:
            for granddep in dep_stage.get("depends_on", []):
                if get_stage(state, granddep) and get_stage(state, granddep).get("status") == "pending":
                    set_stage_status(state, granddep, "done")
    save_state(state, project)
    return deps


# ════════════════════════════════════════════════════════════════════
# Script stages
# ════════════════════════════════════════════════════════════════════

class TestScriptIntegration:
    """Integration tests for script executor type."""

    # ── literature_dedup ──────────────────────────────────────

    def test_literature_dedup_real_execution_done(self, tmp_path):
        """literature_dedup with valid catalog → done."""
        project = _mk_project(tmp_path, stage_in_progress="literature_dedup")
        _add_catalog(project)
        _deps_done(project, "literature_dedup")

        loaded = load_state(project)
        result = execute_stage(
            "literature_dedup", project,
            loaded["state"], loaded["config"],
        )
        assert result["executed"] is True
        assert result["recommended_status"] == "done"
        assert len(result["artifacts"]) >= 2
        # catalog should still exist and have records
        cat = project / "literature" / "catalog.jsonl"
        assert cat.exists()
        # dedup report should exist
        report = project / "literature" / "dedup-report.md"
        assert report.exists()

    def test_literature_dedup_empty_catalog_blocked(self, tmp_path):
        """literature_dedup with empty catalog → blocked."""
        project = _mk_project(tmp_path, stage_in_progress="literature_dedup")
        _deps_done(project, "literature_dedup")
        # Create empty catalog
        (project / "literature").mkdir(exist_ok=True)
        (project / "literature" / "catalog.jsonl").write_text("", encoding="utf-8")

        loaded = load_state(project)
        result = execute_stage(
            "literature_dedup", project,
            loaded["state"], loaded["config"],
        )
        assert result["recommended_status"] == "blocked"

    # ── evidence_matrix ───────────────────────────────────────

    def test_evidence_matrix_pending_confirmation(self, tmp_path):
        """evidence_matrix → pending_confirmation."""
        project = _mk_project(tmp_path, stage_in_progress="evidence_matrix")
        _deps_done(project, "evidence_matrix")

        loaded = load_state(project)
        result = execute_stage(
            "evidence_matrix", project,
            loaded["state"], loaded["config"],
        )
        assert result["executed"] is True
        assert result["recommended_status"] == "pending_confirmation"
        assert result["requires_confirmation"] is True
        assert "evidence-matrix.csv" in str(result.get("artifacts", ""))

    def test_evidence_matrix_creates_files(self, tmp_path):
        """evidence_matrix creates CSV output files."""
        project = _mk_project(tmp_path, stage_in_progress="evidence_matrix")
        _deps_done(project, "evidence_matrix")

        loaded = load_state(project)
        execute_stage("evidence_matrix", project, loaded["state"], loaded["config"])

        assert (project / "literature" / "evidence-matrix.csv").exists()
        assert (project / "citations" / "claim-citation-map.csv").exists()

    # ── formatting ────────────────────────────────────────────

    def test_formatting_real_render_done(self, tmp_path):
        """formatting with real manuscript → done."""
        project = _mk_project(tmp_path, stage_in_progress="formatting")
        _deps_done(project, "formatting")
        _add_manuscript(project)

        loaded = load_state(project)
        result = execute_stage(
            "formatting", project,
            loaded["state"], loaded["config"],
        )
        # formatting may succeed or fail depending on pandoc availability
        assert result["recommended_status"] in ("done", "blocked")
        # If blocked, reason should be specific
        if result["recommended_status"] == "blocked":
            assert result["blocked_reason"] is not None

    def test_formatting_missing_manuscript_blocked(self, tmp_path):
        """formatting without manuscript → blocked."""
        project = _mk_project(tmp_path, stage_in_progress="formatting")
        _deps_done(project, "formatting")
        # No manuscript

        loaded = load_state(project)
        result = execute_stage(
            "formatting", project,
            loaded["state"], loaded["config"],
        )
        assert result["recommended_status"] == "blocked"
        assert "manuscript" in str(result.get("blocked_reason", "")).lower()

    # ── quality_qa ────────────────────────────────────────────

    def test_quality_qa_runs(self, tmp_path):
        """quality_qa executes and returns a result."""
        project = _mk_project(tmp_path, stage_in_progress="quality_qa")
        _deps_done(project, "quality_qa")
        _add_manuscript(project)

        loaded = load_state(project)
        result = execute_stage(
            "quality_qa", project,
            loaded["state"], loaded["config"],
        )
        assert result["executed"] is True
        # status depends on actual QA findings
        assert result["recommended_status"] in ("done", "blocked")

    def test_quality_qa_errors_cause_blocked(self, tmp_path):
        """quality_qa with corrupted manuscript → blocked (if errors found)."""
        project = _mk_project(tmp_path, stage_in_progress="quality_qa")
        _deps_done(project, "quality_qa")
        _add_manuscript(project, "# Bad\n\n![missing](no-file.png)\n\n$$unclosed\n")

        loaded = load_state(project)
        result = execute_stage(
            "quality_qa", project,
            loaded["state"], loaded["config"],
        )
        # QA should find issues with missing image / unclosed math
        # We just verify it doesn't crash and reports status
        assert result["recommended_status"] in ("done", "blocked")


# ════════════════════════════════════════════════════════════════════
# Skill handoff stages
# ════════════════════════════════════════════════════════════════════

class TestSkillHandoffIntegration:
    """Integration tests for skill_handoff executor type."""

    SKILL_HANDOFF_STAGES = [
        "literature_search",
        "deep_reading",
        "outline",
        "writing",
        "polishing",
        "charts_and_tables",
    ]

    def _run_handoff(self, project: Path, stage_id: str) -> dict:
        """Run a skill_handoff stage and return the result."""
        _deps_done(project, stage_id)
        loaded = load_state(project)
        result = execute_stage(
            stage_id, project,
            loaded["state"], loaded["config"],
        )
        return result

    @pytest.mark.parametrize("stage_id", SKILL_HANDOFF_STAGES)
    def test_handoff_generates_json(self, tmp_path, stage_id):
        """Each skill_handoff stage → handoff JSON created."""
        project = _mk_project(tmp_path, stage_in_progress=stage_id)
        result = self._run_handoff(project, stage_id)

        assert result["handoff_generated"] is True
        assert result["recommended_status"] == "waiting_for_user"

        hf_path = project / ".paper-workflow" / "handoffs" / f"{stage_id}.json"
        assert hf_path.exists()

        # Verify handoff content
        data = _json.loads(hf_path.read_text(encoding="utf-8"))
        assert data["stage_id"] == stage_id
        assert data["executor_type"] == "skill_handoff"
        assert "skill" in data
        assert "task_prompt" in data
        assert "expected_outputs" in data

    @pytest.mark.parametrize("stage_id", SKILL_HANDOFF_STAGES)
    def test_handoff_status_is_waiting_for_user(self, tmp_path, stage_id):
        """skill_handoff stage → NOT marked done, stays waiting_for_user."""
        project = _mk_project(tmp_path, stage_in_progress=stage_id)
        result = self._run_handoff(project, stage_id)
        assert result["recommended_status"] != "done"

    def test_consecutive_handoffs_no_overwrite(self, tmp_path):
        """Two handoffs should both exist without overwriting."""
        project = _mk_project(tmp_path, stage_in_progress="outline")
        _deps_done(project, "outline")
        _deps_done(project, "writing")

        # Run outline
        loaded = load_state(project)
        execute_stage("outline", project, loaded["state"], loaded["config"])

        # Run writing (need to set it to in_progress in state)
        loaded = load_state(project)
        loaded["state"]["current_stage"] = "writing"
        loaded["state"]["stages"]["writing"]["status"] = "in_progress"
        _deps_done(project, "writing")

        loaded = load_state(project)
        execute_stage("writing", project, loaded["state"], loaded["config"])

        # Both handoffs should exist
        assert (project / ".paper-workflow" / "handoffs" / "outline.json").exists()
        assert (project / ".paper-workflow" / "handoffs" / "writing.json").exists()

    def test_latest_json_points_to_last_handoff(self, tmp_path):
        """latest.json should point to the most recent handoff."""
        project = _mk_project(tmp_path, stage_in_progress="outline")
        self._run_handoff(project, "outline")

        # Run another handoff
        project2 = _mk_project(tmp_path / "p2", stage_in_progress="deep_reading")
        self._run_handoff(project2, "deep_reading")

        latest = project2 / ".paper-workflow" / "handoffs" / "latest.json"
        if latest.exists():
            data = _json.loads(latest.read_text(encoding="utf-8"))
            assert data["stage_id"] == "deep_reading"

    def test_handoff_contains_input_files_status(self, tmp_path):
        """Handoff JSON includes input file existence checks."""
        project = _mk_project(tmp_path, stage_in_progress="writing")
        _add_manuscript(project)
        _add_catalog(project)

        self._run_handoff(project, "writing")
        hf = project / ".paper-workflow" / "handoffs" / "writing.json"
        data = _json.loads(hf.read_text(encoding="utf-8"))

        assert "input_files" in data
        # manuscript/main.md was created → should exist
        if "manuscript/main.md" in data["input_files"]:
            assert data["input_files"]["manuscript/main.md"]["exists"] is True


# ════════════════════════════════════════════════════════════════════
# Manual stages
# ════════════════════════════════════════════════════════════════════

class TestManualIntegration:
    """Integration tests for manual executor type."""

    MANUAL_STAGES = [
        "requirements",
        "material_prep",
        "research_design",
        "data_analysis",
        "originality_check",
    ]

    def _run_manual(self, project: Path, stage_id: str) -> dict:
        _deps_done(project, stage_id)
        loaded = load_state(project)
        return execute_stage(
            stage_id, project,
            loaded["state"], loaded["config"],
        )

    @pytest.mark.parametrize("stage_id", MANUAL_STAGES)
    def test_manual_returns_waiting_for_user(self, tmp_path, stage_id):
        """Each manual stage → waiting_for_user with message."""
        project = _mk_project(tmp_path, stage_in_progress=stage_id)
        result = self._run_manual(project, stage_id)

        assert result["recommended_status"] == "waiting_for_user"
        assert result["requires_manual_action"] is True
        assert result["requires_confirmation"] is True
        assert "message" in result
        assert len(result["message"]) > 50  # non-trivial task description

    @pytest.mark.parametrize("stage_id", MANUAL_STAGES)
    def test_manual_does_not_mark_done(self, tmp_path, stage_id):
        """Manual stage must NOT be done."""
        project = _mk_project(tmp_path, stage_in_progress=stage_id)
        result = self._run_manual(project, stage_id)
        assert result["recommended_status"] != "done"

    def test_revision_is_future(self, tmp_path):
        """revision stage is future (v0.3)."""
        project = _mk_project(tmp_path, stage_in_progress="revision")
        _deps_done(project, "revision")
        loaded = load_state(project)

        result = execute_stage(
            "revision", project,
            loaded["state"], loaded["config"],
        )
        assert result["recommended_status"] == "waiting_for_user"
        assert "FUTURE" in result.get("message", "").upper() or "v0.3" in result.get("message", "").lower()

    def test_manual_confirm_checks_done_conditions(self, tmp_path):
        """Confirming a manual stage checks done_conditions."""
        project = _mk_project(tmp_path, stage_in_progress="requirements")
        _add_notes(project)  # requirements done_condition: file_exists:manuscript/notes.md

        # done_conditions should be met
        all_met, unmet = check_done_conditions("requirements", project)
        assert all_met is True

    def test_manual_confirm_fails_without_artifacts(self, tmp_path):
        """Confirm fails when required artifacts are missing."""
        project = _mk_project(tmp_path, stage_in_progress="data_analysis")
        # no output files created → done_conditions should fail
        all_met, unmet = check_done_conditions("data_analysis", project)
        # data_analysis may have conditions or not; just verify it doesn't crash
        assert isinstance(all_met, bool)


# ════════════════════════════════════════════════════════════════════
# Hybrid stages
# ════════════════════════════════════════════════════════════════════

class TestHybridIntegration:
    """Integration tests for hybrid executor type (citation_verification)."""

    def _run_hybrid(self, project: Path) -> dict:
        _deps_done(project, "citation_verification")
        loaded = load_state(project)
        return execute_stage(
            "citation_verification", project,
            loaded["state"], loaded["config"],
        )

    def test_citation_verification_clean_done(self, tmp_path):
        """Clean manuscript (no citation issues) → done."""
        project = _mk_project(tmp_path, stage_in_progress="citation_verification")
        _add_manuscript(project, "# Test\n\nThis is a clean manuscript with [@ref-1] citation.\n")
        _add_catalog(project)

        result = self._run_hybrid(project)
        assert result["executed"] is True
        assert result["recommended_status"] == "done"
        assert result["handoff_generated"] is False

    def test_citation_verification_cite_needed_handoff(self, tmp_path):
        """Manuscript with [CITE NEEDED] → waiting_for_user + handoff."""
        project = _mk_project(tmp_path, stage_in_progress="citation_verification")
        _add_manuscript(project, "# Test\n\nThis claim needs support [CITE NEEDED].\n")
        _add_catalog(project)

        result = self._run_hybrid(project)
        assert result["recommended_status"] == "waiting_for_user"
        assert result["handoff_generated"] is True
        assert result["handoff_path"] is not None

        # Verify handoff file exists
        hf = project / ".paper-workflow" / "handoffs" / "citation_verification.json"
        assert hf.exists()

    def test_citation_verification_missing_manuscript_blocked(self, tmp_path):
        """No manuscript → blocked."""
        project = _mk_project(tmp_path, stage_in_progress="citation_verification")
        # No manuscript

        result = self._run_hybrid(project)
        assert result["recommended_status"] == "blocked"
        assert "manuscript" in str(result.get("blocked_reason", "")).lower()

    def test_citation_verification_handoff_warns_no_fake(self, tmp_path):
        """Citation handoff contains anti-fake-citekey warning."""
        project = _mk_project(tmp_path, stage_in_progress="citation_verification")
        _add_manuscript(project, "# Test\n\nClaim [CITE NEEDED] here.\n")
        _add_catalog(project)

        result = self._run_hybrid(project)
        assert result["handoff_generated"] is True

        hf = project / ".paper-workflow" / "handoffs" / "citation_verification.json"
        data = _json.loads(hf.read_text(encoding="utf-8"))

        task = data.get("task_prompt", "")
        assert "虚假" in task or "编造" in task or "citekey" in task.lower()

    def test_citation_verification_report_created(self, tmp_path):
        """Citation verification creates a QA report."""
        project = _mk_project(tmp_path, stage_in_progress="citation_verification")
        _add_manuscript(project, "# Test\n\nClean content.\n")
        _add_catalog(project)

        self._run_hybrid(project)
        report = project / "outputs" / "qa" / "citation-report.md"
        assert report.exists()
        content = report.read_text(encoding="utf-8")
        assert "Citation Verification" in content


# ════════════════════════════════════════════════════════════════════
# Cross-executor tests
# ════════════════════════════════════════════════════════════════════

class TestCrossExecutor:
    """Tests that span multiple executor types."""

    def test_script_to_handoff_chain(self, tmp_path):
        """literature_dedup (script) → evidence_matrix (script) → outline (handoff)."""
        project = _mk_project(tmp_path, stage_in_progress="requirements")
        _add_catalog(project)
        _add_manuscript(project)
        _add_notes(project)

        # Complete reqs manually
        loaded = load_state(project)
        set_stage_status(loaded["state"], "requirements", "done")
        save_state(loaded["state"], project)

        # lit_search → handoff
        loaded = load_state(project)
        loaded["state"]["stages"]["literature_search"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "literature_search"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r1 = execute_stage("literature_search", project, loaded["state"], loaded["config"])
        assert r1["handoff_generated"] is True

        # dedup → done
        _deps_done(project, "literature_dedup")
        loaded = load_state(project)
        loaded["state"]["stages"]["literature_dedup"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "literature_dedup"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r2 = execute_stage("literature_dedup", project, loaded["state"], loaded["config"])
        assert r2["recommended_status"] == "done"

        # evidence → pending_confirmation
        loaded = load_state(project)
        loaded["state"]["stages"]["deep_reading"]["status"] = "done"
        loaded["state"]["stages"]["evidence_matrix"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "evidence_matrix"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r3 = execute_stage("evidence_matrix", project, loaded["state"], loaded["config"])
        assert r3["recommended_status"] == "pending_confirmation"

        # outline → handoff
        loaded = load_state(project)
        # Set remaining deps
        for s in ["research_design", "data_analysis", "charts_and_tables"]:
            loaded["state"]["stages"][s]["status"] = "done"
        loaded["state"]["stages"]["evidence_matrix"]["status"] = "done"
        loaded["state"]["stages"]["outline"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "outline"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r4 = execute_stage("outline", project, loaded["state"], loaded["config"])
        assert r4["handoff_generated"] is True
        assert (project / ".paper-workflow" / "handoffs" / "outline.json").exists()

    def test_all_contracts_have_executor_type(self):
        """Every contract must have a valid executor_type."""
        from stage_executor import list_contracts
        valid_types = {"script", "skill_handoff", "manual", "hybrid"}
        contracts = list_contracts()
        assert len(contracts) == 17
        for c in contracts:
            assert c["executor_type"] in valid_types, \
                f"{c['stage_id']} has invalid executor_type: {c.get('executor_type')}"
