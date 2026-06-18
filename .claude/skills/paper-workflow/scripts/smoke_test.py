#!/usr/bin/env python3
"""Run v0.2 smoke test against mini-paper fixture and generate report."""

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

FIXTURES_DIR = SCRIPTS_DIR.parent / "tests" / "fixtures"
MINI_PAPER = FIXTURES_DIR / "mini-paper"
COMMANDS_PY = SCRIPTS_DIR / "commands.py"

SMOKE_STAGES = [
    "literature_dedup", "evidence_matrix", "outline", "writing",
    "citation_verification", "charts_and_tables", "formatting", "quality_qa",
]

# Stages that need explicit confirm after run (before downstream stages)
NEEDS_CONFIRM = {"evidence_matrix"}

HANDOFF_STAGES = {
    "literature_search", "deep_reading", "outline",
    "writing", "polishing", "charts_and_tables",
}


def _seed_evidence(project_dir: Path):
    """Add data rows so evidence_matrix confirm can pass."""
    import csv

    ev_path = project_dir / "literature" / "evidence-matrix.csv"
    if ev_path.exists():
        with open(ev_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ref-0001", "wang2024RockyDesertification", "desertification",
                "CN", "remote_sensing", "regression",
                "Karst desertification reduces ecosystem services",
                "limited to one region", "intro,methods", "p3", ""
            ])

    claim_path = project_dir / "citations" / "claim-citation-map.csv"
    if claim_path.exists():
        with open(claim_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "C001", "intro", "Desertification is a major issue",
                "ref-0001", "wang2024RockyDesertification", "strong", "yes", ""
            ])


def main():
    # Copy fixture
    work_dir = Path("F:/Temp/smoke-v02")
    if work_dir.exists():
        shutil.rmtree(str(work_dir), ignore_errors=True)
    shutil.copytree(str(MINI_PAPER), str(work_dir))

    # Reset state
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
        "schema_version": 1, "project_id": "smoke-v02",
        "paper_type": "course_paper", "research_type": "review",
        "discipline": "computer_science", "language": "zh",
        "target_journal": None, "current_stage": "requirements",
        "stages": stages, "overrides": [],
    }
    with open(work_dir / ".paper-workflow" / "state.yaml", "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True)

    from workflow_state import load_state, save_state, set_stage_status, get_stage

    def load():
        return load_state(work_dir)

    def save(s):
        save_state(s, work_dir)

    # Complete requirements
    l = load()
    set_stage_status(l["state"], "requirements", "done")
    save(l["state"])

    results = []
    for sid in SMOKE_STAGES:
        l = load()
        stage = get_stage(l["state"], sid)
        # Mark all deps as done (but don't overwrite pending_confirmation/waiting_for_user)
        for d in stage.get("depends_on", []):
            ds = get_stage(l["state"], d)
            if ds and ds.get("status") not in ("done", "skipped", "pending_confirmation", "waiting_for_user"):
                ds["status"] = "done"

        l["state"]["stages"][sid]["status"] = "in_progress"
        l["state"]["current_stage"] = sid
        save(l["state"])

        # Use --override to test each stage independently (avoids dep chain complexity)
        cmd = [sys.executable, str(COMMANDS_PY), "--project", str(work_dir),
               "run", sid, "--override"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        l2 = load()
        final_status = l2["state"]["stages"][sid]["status"]
        hf = work_dir / ".paper-workflow" / "handoffs" / f"{sid}.json"
        hf_yes = "yes" if hf.exists() else "no"

        results.append((sid, r.returncode, final_status, hf_yes))
        print(f"  {sid}: rc={r.returncode}  status={final_status}  handoff={hf_yes}")

        # If stage needs confirmation, seed data and confirm
        if sid in NEEDS_CONFIRM and final_status == "pending_confirmation":
            _seed_evidence(work_dir)
            cmd_confirm = [sys.executable, str(COMMANDS_PY), "--project", str(work_dir),
                           "confirm", sid]
            cr = subprocess.run(cmd_confirm, capture_output=True, text=True, timeout=30)
            l3 = load()
            confirmed_status = l3["state"]["stages"][sid]["status"]
            print(f"    confirm {sid}: rc={cr.returncode}  status={confirmed_status}")
            results.append((f"{sid} (confirmed)", cr.returncode, confirmed_status, hf_yes))

    # ── Build report ──

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
        cwd=str(SCRIPTS_DIR.parent.parent.parent.parent),
    ).stdout.strip()[:8]

    lines = [
        "# paper-workflow v0.2 Smoke Test Report",
        "",
        f"**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Commit**: `{commit}`",
        f"**Project**: tests/fixtures/mini-paper/ (fallback fixture)",
        f"**Branch**: dev/paper-workflow-v0.2-stage-executor",
        "",
        "## Stage Execution Results",
        "",
        "| Stage | Exit | Status | Handoff? |",
        "|-------|------|--------|----------|",
    ]
    for sid, rc, st, hf in results:
        lines.append(f"| {sid} | {rc} | {st} | {hf} |")

    # Outputs
    print("\n  --- outputs/latest ---")
    latest = work_dir / "outputs" / "latest"
    if latest.exists():
        latest_files = [f.name for f in latest.iterdir() if f.is_file()]
        for fn in latest_files:
            print(f"    {fn}")
    else:
        latest_files = []

    lines.append("")
    lines.append("## Outputs")
    lines.append(f"outputs/latest/: {latest_files if latest_files else '(empty)'}")

    # QA
    qa_dir = work_dir / "outputs" / "qa"
    qa_files = [f.name for f in qa_dir.iterdir()] if qa_dir.exists() else []
    print("\n  --- QA files ---")
    for fn in qa_files:
        print(f"    {fn}")

    lines.append("")
    lines.append("## QA Report")
    lines.append(f"QA files: {qa_files if qa_files else '(none)'}")

    # Final state
    l = load()
    print(f"\n  --- Final state ---")
    print(f"  current_stage: {l['state']['current_stage']}")

    lines.append("")
    lines.append("## Final State")
    lines.append(f"current_stage: {l['state']['current_stage']}")

    status_groups = {}
    for sid, s in l["state"]["stages"].items():
        status_groups.setdefault(s["status"], []).append(sid)
    for st in ["done", "waiting_for_user", "pending_confirmation", "in_progress", "blocked", "pending", "skipped"]:
        if st in status_groups:
            line = f"- {st}: {', '.join(status_groups[st])}"
            lines.append(line)
            print(f"    {line}")

    # Bugs check — only verify stages that were actually executed
    bugs = []
    handoff_in_smoke = HANDOFF_STAGES & set(SMOKE_STAGES)
    for sid in handoff_in_smoke:
        s = get_stage(l["state"], sid)
        if s and s["status"] == "done":
            bugs.append(f"BUG: {sid} (skill_handoff) wrongfully marked done — should be waiting_for_user")

    for sid, s in l["state"]["stages"].items():
        if s["status"] == "done" and s.get("blockers"):
            bugs.append(f"BUG: {sid} marked done but has blockers: {s['blockers']}")

    lines.append("")
    if bugs:
        lines.append("## Bugs Found")
        for b in bugs:
            lines.append(f"- {b}")
    else:
        lines.append("## Bugs Found")
        lines.append("None — no critical bugs detected.")

    lines.append("")
    lines.append("## Recommendation")
    if not bugs:
        lines.append("- ✅ Recommend tagging **v0.2.0**")
    else:
        lines.append("- ⚠️ Fix bugs before tagging v0.2.0")
    lines.append("- ✅ Merging dev/paper-workflow-v0.2-stage-executor → master after review")

    # Write report
    repo_root = SCRIPTS_DIR.parent.parent.parent.parent
    report_path = repo_root / "docs" / "superpowers" / "reports" / "2026-06-18-paper-workflow-v0.2-smoke-test.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n  Report saved: {report_path}")
    if bugs:
        print(f"  WARNING: {len(bugs)} bugs found!")
        return 1
    else:
        print("  No critical bugs detected.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
