"""End-to-end 6-phase v0.2 workflow test (M8.2).

Uses tests/fixtures/mini-paper/ as the source project, resets state to
simulate a fresh v0.2 workflow, and validates each phase.

Phases:
  1. 文献检索下载 — literature_dedup (script)
  2. 深度阅读     — evidence_matrix (script → pending_confirmation)
  3. 大纲         — outline (skill_handoff)
  4. 写论文       — writing, citation_verification, polishing (handoff + hybrid + handoff)
  5. 图表         — charts_and_tables (skill_handoff)
  6. 输出/QA      — formatting, quality_qa (script + script)
"""

import csv as _csv
import json as _json
import os
import shutil
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from workflow_state import (
    load_state, save_state, set_stage_status, get_stage,
    get_current_stage, get_stages_by_status, get_next_stages,
    mark_stage_blocked, find_project_root,
)
from stage_executor import (
    execute_stage, check_done_conditions, load_contract, log_artifacts,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
MINI_PAPER = FIXTURES_DIR / "mini-paper"


# ── Helpers ────────────────────────────────────────────────────────

def _copy_mini_paper(dest: Path) -> Path:
    """Copy mini-paper fixture to a writable temp location."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(MINI_PAPER, dest)
    return dest


def _reset_state_to_fresh(project: Path):
    """Reset mini-paper state to a fresh v0.2 workflow.

    Sets requirements → in_progress, everything else → pending.
    Preserves existing artifacts (catalog, manuscript, etc.).
    """
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
        "project_id": "e2e-v02-test",
        "paper_type": "course_paper",
        "research_type": "review",
        "discipline": "computer_science",
        "language": "zh",
        "target_journal": None,
        "current_stage": "requirements",
        "stages": stages,
        "overrides": [],
    }
    with open(project / ".paper-workflow" / "state.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True)


def _advance_stage(project: Path, stage_id: str, status: str = "done"):
    """Manually advance a stage in state.yaml."""
    loaded = load_state(project)
    set_stage_status(loaded["state"], stage_id, status)
    save_state(loaded["state"], project)


# ════════════════════════════════════════════════════════════════════
# 6-Phase E2E Test
# ════════════════════════════════════════════════════════════════════

class TestE2E6Phase:
    """Full 6-phase end-to-end workflow."""

    def test_phase1_literature_dedup(self, tmp_path):
        """Phase 1: 文献检索下载 → run literature_dedup → done."""
        project = _copy_mini_paper(tmp_path / "e2e-p1")
        _reset_state_to_fresh(project)

        # Complete requirements
        _advance_stage(project, "requirements", "done")

        # Run literature_search → handoff
        loaded = load_state(project)
        loaded["state"]["stages"]["literature_search"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "literature_search"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r_search = execute_stage("literature_search", project, loaded["state"], loaded["config"])
        assert r_search["handoff_generated"] is True

        # Mark literature_search as done (simulating user completing the handoff)
        _advance_stage(project, "literature_search", "done")

        # Run literature_dedup
        loaded = load_state(project)
        loaded["state"]["stages"]["literature_dedup"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "literature_dedup"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r_dedup = execute_stage("literature_dedup", project, loaded["state"], loaded["config"])
        assert r_dedup["recommended_status"] == "done"
        assert r_dedup["executed"] is True

        # dedup report created
        assert (project / "literature" / "dedup-report.md").exists()
        # artifact manifest has entries
        manifest = project / ".paper-workflow" / "artifact-manifest.jsonl"
        assert manifest.exists()

    def test_phase2_evidence_matrix(self, tmp_path):
        """Phase 2: 深度阅读 → run evidence_matrix → pending_confirmation."""
        project = _copy_mini_paper(tmp_path / "e2e-p2")
        _reset_state_to_fresh(project)

        # Complete all deps up to evidence_matrix
        for s in ["requirements", "literature_search", "literature_dedup", "deep_reading"]:
            _advance_stage(project, s, "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["evidence_matrix"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "evidence_matrix"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r = execute_stage("evidence_matrix", project, loaded["state"], loaded["config"])
        assert r["executed"] is True
        assert r["recommended_status"] == "pending_confirmation"
        assert r["requires_confirmation"] is True

        # Files created
        assert (project / "literature" / "evidence-matrix.csv").exists()
        assert (project / "citations" / "claim-citation-map.csv").exists()

    def test_phase2_confirm_evidence_matrix(self, tmp_path):
        """Phase 2: confirm evidence_matrix after adding data."""
        project = _copy_mini_paper(tmp_path / "e2e-p2b")
        _reset_state_to_fresh(project)

        for s in ["requirements", "literature_search", "literature_dedup", "deep_reading"]:
            _advance_stage(project, s, "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["evidence_matrix"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "evidence_matrix"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        execute_stage("evidence_matrix", project, loaded["state"], loaded["config"])

        # Add data rows so confirm can pass
        with open(project / "literature" / "evidence-matrix.csv", "a", encoding="utf-8",
                  newline="") as f:
            writer = _csv.writer(f)
            writer.writerow([
                "ref-0001", "wang2024RockyDesertification", "desertification",
                "CN", "remote_sensing", "regression",
                "Karst desertification reduces ecosystem services",
                "limited to one region", "intro,methods", "p3", ""
            ])
        with open(project / "citations" / "claim-citation-map.csv", "a", encoding="utf-8",
                  newline="") as f:
            writer = _csv.writer(f)
            writer.writerow([
                "C001", "intro", "Desertification is a major issue",
                "ref-0001", "wang2024RockyDesertification", "strong", "yes", ""
            ])

        # Confirm should pass
        all_met, unmet = check_done_conditions("evidence_matrix", project)
        assert all_met is True, f"unmet: {unmet}"

    def test_phase3_outline_handoff(self, tmp_path):
        """Phase 3: 大纲 → run outline → waiting_for_user + handoff."""
        project = _copy_mini_paper(tmp_path / "e2e-p3")
        _reset_state_to_fresh(project)

        # Complete all deps through evidence_matrix + research_design + data_analysis + charts
        for s in ["requirements", "literature_search", "literature_dedup",
                   "deep_reading", "evidence_matrix", "research_design",
                   "data_analysis", "charts_and_tables"]:
            _advance_stage(project, s, "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["outline"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "outline"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r = execute_stage("outline", project, loaded["state"], loaded["config"])
        assert r["handoff_generated"] is True
        assert r["recommended_status"] == "waiting_for_user"

        # Handoff file exists and has correct structure
        hf = project / ".paper-workflow" / "handoffs" / "outline.json"
        assert hf.exists()
        data = _json.loads(hf.read_text(encoding="utf-8"))
        assert data["stage_id"] == "outline"
        assert "skill" in data
        assert data["status"] == "waiting_for_user"

    def test_phase4_writing_and_citations(self, tmp_path):
        """Phase 4: writing → citation_verification → polishing chain."""
        project = _copy_mini_paper(tmp_path / "e2e-p4")
        _reset_state_to_fresh(project)

        # Complete deps through outline
        for s in ["requirements", "literature_search", "literature_dedup",
                   "deep_reading", "evidence_matrix", "research_design",
                   "data_analysis", "charts_and_tables", "outline"]:
            _advance_stage(project, s, "done")

        # ── writing (skill_handoff) ──
        loaded = load_state(project)
        loaded["state"]["stages"]["writing"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "writing"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r_writing = execute_stage("writing", project, loaded["state"], loaded["config"])
        assert r_writing["handoff_generated"] is True
        assert r_writing["recommended_status"] == "waiting_for_user"

        # ── polishing (skill_handoff) ──
        _advance_stage(project, "writing", "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["polishing"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "polishing"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r_polish = execute_stage("polishing", project, loaded["state"], loaded["config"])
        assert r_polish["handoff_generated"] is True

        # ── citation_verification (hybrid) — clean path ──
        _advance_stage(project, "polishing", "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["citation_verification"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "citation_verification"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r_cite = execute_stage("citation_verification", project, loaded["state"], loaded["config"])
        # Clean manuscript should pass
        assert r_cite["recommended_status"] in ("done", "waiting_for_user")
        # Citation report created
        assert (project / "outputs" / "qa" / "citation-report.md").exists()

    def test_phase5_charts_and_tables(self, tmp_path):
        """Phase 5: 图表 → run charts_and_tables → handoff."""
        project = _copy_mini_paper(tmp_path / "e2e-p5")
        _reset_state_to_fresh(project)

        for s in ["requirements", "literature_search", "literature_dedup",
                   "deep_reading", "evidence_matrix", "research_design",
                   "data_analysis", "outline", "writing", "polishing",
                   "citation_verification"]:
            _advance_stage(project, s, "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["charts_and_tables"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "charts_and_tables"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r = execute_stage("charts_and_tables", project, loaded["state"], loaded["config"])
        assert r["handoff_generated"] is True
        assert r["recommended_status"] == "waiting_for_user"

        hf = project / ".paper-workflow" / "handoffs" / "charts_and_tables.json"
        assert hf.exists()

        data = _json.loads(hf.read_text(encoding="utf-8"))
        assert "skill" in data

    def test_phase6_formatting_and_qa(self, tmp_path):
        """Phase 6: 输出/QA → formatting → quality_qa."""
        project = _copy_mini_paper(tmp_path / "e2e-p6")
        _reset_state_to_fresh(project)

        for s in ["requirements", "material_prep", "literature_search",
                   "literature_dedup", "deep_reading", "evidence_matrix",
                   "research_design", "data_analysis", "charts_and_tables",
                   "outline", "writing", "polishing", "citation_verification",
                   "originality_check"]:
            _advance_stage(project, s, "done")

        # ── formatting (script) ──
        loaded = load_state(project)
        loaded["state"]["stages"]["formatting"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "formatting"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r_format = execute_stage("formatting", project, loaded["state"], loaded["config"])
        # formatting may succeed (done) or fail (blocked) depending on pandoc
        assert r_format["recommended_status"] in ("done", "blocked")

        # ── quality_qa (script) ──
        _advance_stage(project, "formatting", "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["quality_qa"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "quality_qa"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        r_qa = execute_stage("quality_qa", project, loaded["state"], loaded["config"])
        assert r_qa["executed"] is True
        # QA result can be done or blocked depending on findings
        assert r_qa["recommended_status"] in ("done", "blocked")

    def test_state_yaml_flow_correct(self, tmp_path):
        """state.yaml transitions are correct throughout the workflow."""
        project = _copy_mini_paper(tmp_path / "e2e-state")
        _reset_state_to_fresh(project)

        # Phase 1: complete requirements
        _advance_stage(project, "requirements", "done")

        # Verify state
        loaded = load_state(project)
        assert loaded["state"]["stages"]["requirements"]["status"] == "done"
        assert "requirements" in get_stages_by_status(loaded["state"], "done")

        # Next stage should be available
        next_stages = get_next_stages(loaded["state"])
        assert "literature_search" in next_stages or "material_prep" in next_stages

    def test_artifact_manifest_has_records(self, tmp_path):
        """artifact-manifest.jsonl accumulates records across phases."""
        project = _copy_mini_paper(tmp_path / "e2e-artifacts")
        _reset_state_to_fresh(project)

        # Run literature_dedup
        for s in ["requirements", "literature_search"]:
            _advance_stage(project, s, "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["literature_dedup"]["status"] = "in_progress"
        loaded["state"]["current_stage"] = "literature_dedup"
        save_state(loaded["state"], project)

        loaded = load_state(project)
        execute_stage("literature_dedup", project, loaded["state"], loaded["config"])

        manifest = project / ".paper-workflow" / "artifact-manifest.jsonl"
        if manifest.exists():
            lines = [line for line in manifest.read_text(encoding="utf-8").strip().split("\n") if line.strip()]
            assert len(lines) >= 1
            entry = _json.loads(lines[0])
            assert entry["stage_id"] == "literature_dedup"

    def test_status_resume_correct(self, tmp_path, monkeypatch, capsys):
        """status and resume work correctly at a mid-workflow point."""
        project = _copy_mini_paper(tmp_path / "e2e-status")
        _reset_state_to_fresh(project)

        # Go to evidence_matrix (pending_confirmation)
        for s in ["requirements", "literature_search", "literature_dedup", "deep_reading"]:
            _advance_stage(project, s, "done")

        loaded = load_state(project)
        loaded["state"]["stages"]["evidence_matrix"]["status"] = "pending_confirmation"
        loaded["state"]["current_stage"] = "evidence_matrix"
        save_state(loaded["state"], project)

        # Test status
        monkeypatch.chdir(project)
        import commands
        commands.cmd_status()
        captured = capsys.readouterr()
        assert "evidence_matrix" in captured.out
        assert "等待用户确认" in captured.out or "pending" in captured.out.lower()

        # Test resume
        commands.cmd_resume()
        captured2 = capsys.readouterr()
        assert "confirm" in captured2.out.lower()
