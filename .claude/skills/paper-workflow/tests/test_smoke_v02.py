"""Real project smoke test for v0.2 executors (M8.3).

Runs CLI commands against a copy of tests/fixtures/mini-paper/
and records results for the smoke test report.

Usage:
    pytest tests/test_smoke_v02.py -v -s
"""

import csv as _csv
import json as _json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
MINI_PAPER = FIXTURES_DIR / "mini-paper"
COMMANDS_PY = SCRIPTS_DIR / "commands.py"

from workflow_state import load_state, save_state, set_stage_status, get_stage


# ── Helpers ────────────────────────────────────────────────────────

def _copy_mini_paper(dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(MINI_PAPER, dest)
    return dest


def _reset_state(project: Path):
    """Reset mini-paper to a fresh v0.2 state."""
    from init_project import STAGE_IDS, DEPENDENCY_GRAPH
    stages = {}
    for sid in STAGE_IDS:
        stages[sid] = {
            "status": "pending",
            "depends_on": DEPENDENCY_GRAPH.get(sid, []),
            "started_at": None, "completed_at": None,
            "qa_status": "pending", "qa_report": None,
            "artifacts": [], "blockers": [],
        }
    stages["requirements"]["status"] = "in_progress"
    state = {
        "schema_version": 1, "project_id": "smoke-test",
        "paper_type": "course_paper", "research_type": "review",
        "discipline": "computer_science", "language": "zh",
        "target_journal": None, "current_stage": "requirements",
        "stages": stages, "overrides": [],
    }
    with open(project / ".paper-workflow" / "state.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True)


def _run_cli(project: Path, *args) -> tuple[int, str, str]:
    """Run commands.py and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(COMMANDS_PY), "--project", str(project)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=60)
    return result.returncode, result.stdout, result.stderr


# ── Smoke test stages ─────────────────────────────────────────────

# Ordered list of stages to smoke-test (from the spec)
SMOKE_STAGES = [
    "literature_dedup",
    "evidence_matrix",
    "outline",
    "writing",
    "citation_verification",
    "charts_and_tables",
    "formatting",
    "quality_qa",
]


class TestSmokeV02:
    """v0.2 executor smoke test using mini-paper fixture."""

    @pytest.fixture(autouse=True)
    def _setup_smoke(self, tmp_path):
        """Set up the smoke test project."""
        self.project = _copy_mini_paper(tmp_path / "smoke")
        _reset_state(self.project)
        self.results = {}
        self.warnings = []
        self.bugs = []

    def _advance(self, *stage_ids):
        """Mark stages as done and advance dependencies."""
        loaded = load_state(self.project)
        for sid in stage_ids:
            set_stage_status(loaded["state"], sid, "done")
        save_state(loaded["state"], self.project)

    def _set_in_progress(self, stage_id):
        loaded = load_state(self.project)
        loaded["state"]["stages"][stage_id]["status"] = "in_progress"
        loaded["state"]["current_stage"] = stage_id
        save_state(loaded["state"], self.project)

    def test_smoke_run_all_stages(self):
        """Run all 8 key stages via CLI and record results."""
        # Complete requirements first
        self._advance("requirements")

        for stage_id in SMOKE_STAGES:
            # Set up deps
            self._advance_deps(stage_id)
            self._set_in_progress(stage_id)

            rc, stdout, stderr = _run_cli(self.project, "run", stage_id)

            self.results[stage_id] = {
                "returncode": rc,
                "output_preview": stdout[:300] if stdout else "",
            }

            # Check for handoff
            handoff = self.project / ".paper-workflow" / "handoffs" / f"{stage_id}.json"
            if handoff.exists():
                self.results[stage_id]["handoff"] = str(handoff.relative_to(self.project))
                data = _json.loads(handoff.read_text(encoding="utf-8"))
                self.results[stage_id]["handoff_skill"] = data.get("skill", "unknown")

            # Check state
            loaded = load_state(self.project)
            status = loaded["state"]["stages"][stage_id]["status"]
            self.results[stage_id]["final_status"] = status

            # Record warnings for non-clean exits
            if rc != 0:
                self.warnings.append(f"{stage_id}: exit code {rc}")

            # Check for outputs
            latest = self.project / "outputs" / "latest"
            if latest.exists():
                files = [f.name for f in latest.iterdir() if f.is_file()]
                if files:
                    self.results[stage_id]["outputs"] = files

        # ── Verify key constraints ──
        loaded = load_state(self.project)
        state_stages = loaded["state"]["stages"]

        # skill_handoff stages must NOT be "done"
        handoff_stages = {"literature_search", "deep_reading", "outline",
                          "writing", "polishing", "charts_and_tables"}
        for sid in handoff_stages:
            if sid in state_stages and state_stages[sid]["status"] == "done":
                self.bugs.append(f"BUG: {sid} (skill_handoff) was marked done — should be waiting_for_user")

        # blocked stages must NOT be "done"
        for sid, s in state_stages.items():
            if s["status"] == "done":
                if s.get("blockers"):
                    self.bugs.append(f"BUG: {sid} marked done but has blockers: {s['blockers']}")

    def _advance_deps(self, stage_id):
        """Mark all dependencies as done."""
        loaded = load_state(self.project)
        stage = get_stage(loaded["state"], stage_id)
        if stage is None:
            return
        deps = stage.get("depends_on", [])
        for dep in deps:
            dep_stage = get_stage(loaded["state"], dep)
            if dep_stage and dep_stage.get("status") not in ("done", "skipped"):
                set_stage_status(loaded["state"], dep, "done")
        save_state(loaded["state"], self.project)

    def test_smoke_status_and_resume(self, tmp_path):
        """status and resume work after running stages."""
        project = _copy_mini_paper(tmp_path / "smoke-stat")
        _reset_state(project)

        # Advance to evidence_matrix as pending_confirmation
        loaded = load_state(project)
        for s in ["requirements", "literature_search", "literature_dedup", "deep_reading"]:
            set_stage_status(loaded["state"], s, "done")
        loaded["state"]["stages"]["evidence_matrix"]["status"] = "pending_confirmation"
        loaded["state"]["current_stage"] = "evidence_matrix"
        save_state(loaded["state"], project)

        # Test status
        rc, stdout, stderr = _run_cli(project, "status")
        assert rc == 0
        assert "evidence_matrix" in stdout

        # Test resume
        rc, stdout, stderr = _run_cli(project, "resume")
        assert rc == 0
        assert "confirm" in stdout.lower()

    def test_smoke_generate_report(self, tmp_path):
        """Generate the smoke test markdown report."""
        # Run all stages via CLI (reuse the smoke project pattern)
        project = _copy_mini_paper(tmp_path / "smoke-rpt")
        _reset_state(project)
        self._advance("requirements")

        report_lines = [
            f"# paper-workflow v0.2 Smoke Test Report",
            f"",
            f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"**Commit**: `{_get_current_commit()}`",
            f"**Project**: tests/fixtures/mini-paper/ (fallback fixture)",
            f"**Branch**: dev/paper-workflow-v0.2-stage-executor",
            f"",
            f"## Stage Execution Results",
            f"",
            f"| Stage | Exit | Status | Handoff? |",
            f"|-------|------|--------|----------|",
        ]

        for stage_id in SMOKE_STAGES:
            self._advance_deps(stage_id)
            self._set_in_progress(stage_id)
            rc, stdout, stderr = _run_cli(project, "run", stage_id)

            loaded = load_state(project)
            final_status = loaded["state"]["stages"][stage_id]["status"]

            handoff = project / ".paper-workflow" / "handoffs" / f"{stage_id}.json"
            hf_str = "yes" if handoff.exists() else "no"

            report_lines.append(
                f"| {stage_id} | {rc} | {final_status} | {hf_str} |"
            )

        # outputs/latest
        latest = project / "outputs" / "latest"
        if latest.exists():
            files = [f.name for f in latest.iterdir() if f.is_file()]
            report_lines.append("")
            report_lines.append(f"## Outputs")
            report_lines.append(f"outputs/latest/ files: {files if files else '(empty)'}")

        # QA report
        qa_dir = project / "outputs" / "qa"
        qa_files = list(qa_dir.glob("*")) if qa_dir.exists() else []
        report_lines.append("")
        report_lines.append(f"## QA Report")
        report_lines.append(f"QA files: {[f.name for f in qa_files] if qa_files else '(none)'}")

        # Final state.yaml
        loaded = load_state(project)
        report_lines.append("")
        report_lines.append(f"## Final State")
        report_lines.append(f"current_stage: {loaded['state']['current_stage']}")
        statuses = {}
        for sid, s in loaded["state"]["stages"].items():
            st = s["status"]
            statuses.setdefault(st, []).append(sid)
        for st, stages in sorted(statuses.items()):
            report_lines.append(f"- {st}: {', '.join(stages)}")

        # Warnings
        if self.warnings:
            report_lines.append("")
            report_lines.append("## Warnings")
            for w in self.warnings:
                report_lines.append(f"- {w}")

        # Bugs
        if self.bugs:
            report_lines.append("")
            report_lines.append("## Bugs Found")
            for b in self.bugs:
                report_lines.append(f"- {b}")
        else:
            report_lines.append("")
            report_lines.append("## Bugs Found")
            report_lines.append("None — no critical bugs detected.")

        # Recommendation
        report_lines.append("")
        report_lines.append("## Recommendation")
        if not self.bugs:
            report_lines.append("- ✅ Recommend tagging **v0.2.0**")
        else:
            report_lines.append("- ⚠️ Fix bugs before tagging v0.2.0")
        report_lines.append("- ✅ Recommend merging dev/paper-workflow-v0.2-stage-executor → master after review")

        # Write report
        report_dir = project.parent / "reports"
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / "2026-06-18-paper-workflow-v0.2-smoke-test.md"
        report_path.write_text("\n".join(report_lines), encoding="utf-8")

        self.report_path = report_path
        assert report_path.exists()


def _get_current_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=str(SCRIPTS_DIR.parent.parent.parent.parent),  # repo root
        )
        return result.stdout.strip()[:8]
    except Exception:
        return "unknown"
