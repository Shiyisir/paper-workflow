#!/usr/bin/env python3
"""Core state machine for paper-workflow.

Reads and writes .paper-workflow/state.yaml and config.yaml.
All paths are relative to the paper project root (cwd by default).

Atomic writes: save_state() writes to a temp file then renames.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsonschema
import yaml


# Schema loaded lazily
_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "workflow-state.schema.json"
_schema_cache: dict | None = None


def _load_schema() -> dict:
    """Load the workflow-state JSON Schema (cached)."""
    global _schema_cache
    if _schema_cache is None:
        with open(_SCHEMA_PATH, encoding="utf-8") as f:
            _schema_cache = json.load(f)
    return _schema_cache


def find_project_root(start: Path | None = None) -> Path | None:
    """Find the paper project root by looking for .paper-workflow/ directory.

    Searches upward from `start` (default: cwd) until a directory containing
    .paper-workflow/state.yaml or .paper-workflow/config.yaml is found.

    Returns the project root Path, or None if not found.
    """
    current = (start or Path.cwd()).resolve()
    for _ in range(10):  # max 10 levels up
        pw_dir = current / ".paper-workflow"
        if (pw_dir / "state.yaml").exists() or (pw_dir / "config.yaml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def get_pw_dir(project_dir: Path | None = None) -> Path:
    """Get the .paper-workflow directory path."""
    root = project_dir or find_project_root()
    if root is None:
        raise FileNotFoundError(
            "找不到 .paper-workflow/ 目录。请在论文项目根目录下运行，"
            "或先运行 /paper-workflow init。"
        )
    pw_dir = root / ".paper-workflow"
    pw_dir.mkdir(parents=True, exist_ok=True)
    return pw_dir


def init_state(project_id: str, config: dict) -> dict:
    """Create a brand-new state.yaml dict from scratch.

    This is called by init_project.py, not directly by the state machine.
    """
    from init_project import STAGE_IDS, DEPENDENCY_GRAPH, SKIP_MAP

    paper_type = config.get("paper_type", "course_paper")
    research_type = config.get("research_type", "review")
    skip_list = SKIP_MAP.get(paper_type, [])

    now = datetime.now(timezone.utc).isoformat()

    stages = {}
    for sid in STAGE_IDS:
        skipped = sid in skip_list
        if research_type == "theoretical" and sid == "data_analysis":
            skipped = True

        status = "skipped" if skipped else "pending"
        stages[sid] = {
            "status": status,
            "depends_on": DEPENDENCY_GRAPH.get(sid, []),
            "started_at": None,
            "completed_at": None,
            "qa_status": "pending",
            "qa_report": None,
            "artifacts": [],
            "blockers": [],
        }

    stages["requirements"]["status"] = "in_progress"
    stages["requirements"]["started_at"] = now

    state = {
        "schema_version": 1,
        "project_id": project_id,
        "paper_type": config.get("paper_type"),
        "research_type": config.get("research_type"),
        "discipline": config.get("discipline"),
        "language": config.get("language"),
        "target_journal": config.get("target_journal"),
        "current_stage": "requirements",
        "stages": stages,
        "overrides": [],
    }

    return state


def load_state(project_dir: Path | None = None) -> dict:
    """Load state.yaml and merge with config.yaml.

    Returns a dict with keys: 'state' (state.yaml content) and
    'config' (config.yaml content).

    Raises FileNotFoundError if neither file exists.
    """
    pw_dir = get_pw_dir(project_dir)

    state_path = pw_dir / "state.yaml"
    config_path = pw_dir / "config.yaml"

    if not state_path.exists() and not config_path.exists():
        raise FileNotFoundError(
            f"未找到项目状态文件。请确保在论文项目目录下运行，"
            f"或运行 /paper-workflow init 初始化项目。\n"
            f"查找路径: {pw_dir}"
        )

    state = {}
    if state_path.exists():
        with open(state_path, encoding="utf-8") as f:
            state = yaml.safe_load(f) or {}

    config = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    return {"state": state, "config": config}


def save_state(state: dict, project_dir: Path | None = None) -> Path:
    """Atomically write state dict to state.yaml.

    Uses temp file + rename to avoid corrupting the state file on write failure.
    Returns the path to the written file.
    """
    pw_dir = get_pw_dir(project_dir)
    state_path = pw_dir / "state.yaml"

    # Atomic write: write to temp file in same directory, then rename
    # (os.replace is atomic on POSIX; on Windows it's near-atomic
    #  and requires the target to exist or be replaced)
    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=".yaml", prefix=".state-", dir=str(pw_dir)
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            yaml.dump(
                state, f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        os.replace(tmp_path, state_path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return state_path


def validate_state(state: dict) -> list[str]:
    """Validate state dict against the JSON Schema.

    Returns a list of error messages. Empty list means valid.
    Does NOT raise on validation failure.
    """
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    errors = list(validator.iter_errors(state))
    return [e.message for e in errors]


# ---------------------------------------------------------------------------
# Stage status helpers (minimal — full transition logic in M2.2)
# ---------------------------------------------------------------------------

def get_stage(state: dict, stage_id: str) -> dict | None:
    """Get a single stage's data from state dict."""
    return state.get("stages", {}).get(stage_id)


def get_current_stage(state: dict) -> str:
    """Get the current_stage identifier."""
    return state.get("current_stage", "requirements")


def list_stages(state: dict) -> list[str]:
    """List all stage IDs in dependency order."""
    return list(state.get("stages", {}).keys())


def is_stage_done(state: dict, stage_id: str) -> bool:
    """Check if a stage is done (or skipped)."""
    stage = get_stage(state, stage_id)
    if stage is None:
        return False
    return stage.get("status") in ("done", "skipped")


def get_stages_by_status(state: dict, status: str) -> list[str]:
    """Get stage IDs with a given status."""
    return [
        sid for sid, s in state.get("stages", {}).items()
        if s.get("status") == status
    ]


# ---------------------------------------------------------------------------
# Stage transition logic (M2.2)
# ---------------------------------------------------------------------------

def _check_dependencies(state: dict, stage_id: str) -> list[str]:
    """Return list of unmet dependencies for a stage.

    A dependency is unmet if its status is NOT 'done' or 'skipped'.
    """
    stage = get_stage(state, stage_id)
    if stage is None:
        return [f"阶段 '{stage_id}' 不存在"]

    unmet = []
    for dep_id in stage.get("depends_on", []):
        if not is_stage_done(state, dep_id):
            unmet.append(dep_id)
    return unmet


def set_stage_status(
    state: dict,
    stage_id: str,
    status: str,
    override: bool = False,
) -> dict:
    """Attempt to set a stage's status.

    Args:
        state: The full state dict (mutated in place).
        stage_id: Target stage identifier.
        status: Target status ('in_progress', 'done', etc.).
        override: If True, skip dependency checking and log to overrides.

    Returns:
        {
            "success": bool,
            "message": str,
            "blocked_deps": [str, ...],   # unmet dependencies (if any)
            "overridden": bool,
        }
    """
    now = datetime.now(timezone.utc).isoformat()
    stage = get_stage(state, stage_id)

    if stage is None:
        return {
            "success": False,
            "message": f"未知阶段: '{stage_id}'。可用阶段: {', '.join(list_stages(state))}",
            "blocked_deps": [],
            "overridden": False,
        }

    valid_statuses = {"pending", "in_progress", "done", "skipped", "blocked"}
    if status not in valid_statuses:
        return {
            "success": False,
            "message": f"无效状态: '{status}'。有效值: {valid_statuses}",
            "blocked_deps": [],
            "overridden": False,
        }

    if not override:
        # Check dependencies
        unmet = _check_dependencies(state, stage_id)
        if unmet:
            # Mark as blocked instead
            stage["status"] = "blocked"
            stage["blockers"] = [
                f"前置阶段未完成: {', '.join(unmet)}",
            ]
            state["current_stage"] = stage_id
            return {
                "success": False,
                "message": f"阶段 '{stage_id}' 被阻塞。未完成的依赖: {', '.join(unmet)}",
                "blocked_deps": unmet,
                "overridden": False,
            }

    # Proceed with status change
    if override and status in ("done", "in_progress"):
        # Log the override
        unmet = _check_dependencies(state, stage_id)
        overrides = state.setdefault("overrides", [])
        overrides.append({
            "stage": stage_id,
            "timestamp": now,
            "reason": f"强制推进: {status}",
            "missing_deps": unmet,
        })

    old_status = stage.get("status")
    stage["status"] = status
    state["current_stage"] = stage_id

    if status == "in_progress" and old_status != "in_progress":
        stage["started_at"] = now
    elif status == "done":
        stage["completed_at"] = now
        # Clear blockers on successful completion
        stage["blockers"] = []

    return {
        "success": True,
        "message": f"阶段 '{stage_id}': {old_status} → {status}",
        "blocked_deps": [],
        "overridden": override,
    }


def get_next_stages(state: dict) -> list[str]:
    """Return stages where all depends_on are satisfied and status is 'pending'.

    Does NOT return stages that are blocked, in_progress, done, or skipped.
    """
    next_stages = []
    for sid in list_stages(state):
        stage = get_stage(state, sid)
        if stage is None:
            continue
        if stage.get("status") != "pending":
            continue
        unmet = _check_dependencies(state, sid)
        if not unmet:
            next_stages.append(sid)
    return next_stages


def get_blocked_stages(state: dict) -> list[dict]:
    """Return list of blocked stages with their reasons.

    Each item: {"stage_id": str, "blockers": [str], "status": str}
    """
    blocked = []
    for sid in list_stages(state):
        stage = get_stage(state, sid)
        if stage is None:
            continue
        if stage.get("status") == "blocked":
            blocked.append({
                "stage_id": sid,
                "blockers": stage.get("blockers", []),
                "status": "blocked",
            })
    return blocked


def mark_stage_blocked(state: dict, stage_id: str, reason: str) -> None:
    """Mark a stage as blocked with a custom reason.

    Raises ValueError if the stage doesn't exist.
    Mutates state in place.
    """
    stage = get_stage(state, stage_id)
    if stage is None:
        raise ValueError(f"未知阶段: '{stage_id}'")
    stage["status"] = "blocked"
    blockers = stage.get("blockers", [])
    if reason not in blockers:
        blockers.append(reason)
    stage["blockers"] = blockers
    state["current_stage"] = stage_id
