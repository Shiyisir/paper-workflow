#!/usr/bin/env python3
"""Stage executor framework for paper-workflow v0.2.

Provides contract loading, done-conditions checking, artifact logging,
and a typed dispatcher that routes stages to the correct executor type.

IMPORTANT: This module does NOT:
  - modify commands.py
  - replace _execute_stage() stub
  - call dedup.py / render.py / qa_report.py directly (stubs in v0.2)
  - import nature-reader / nature-writing / nature-figure
  - write state.yaml (status writes are commands.py's job in M7)
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import yaml

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_CONTRACTS_DIR = _SCRIPT_DIR.parent / "contracts"
_SCHEMA_PATH = _SCRIPT_DIR.parent / "schemas" / "stage-execution.schema.json"

_schema_cache: dict | None = None


def _load_schema() -> dict:
    global _schema_cache
    if _schema_cache is None:
        with open(_SCHEMA_PATH, encoding="utf-8") as f:
            _schema_cache = json.load(f)
    return _schema_cache


# ---------------------------------------------------------------------------
# M2.1: Contract Loader
# ---------------------------------------------------------------------------

def load_contract(stage_id: str) -> dict:
    """Load a single stage execution contract from YAML.

    Args:
        stage_id: 17-stage identifier (e.g., 'literature_search').

    Returns:
        Contract dict.

    Raises:
        FileNotFoundError: if contract file does not exist.
        ValueError: if contract fails schema validation.
    """
    contract_path = _CONTRACTS_DIR / f"{stage_id}.yaml"
    if not contract_path.exists():
        raise FileNotFoundError(
            f"Contract not found for stage '{stage_id}'. "
            f"Expected: {contract_path}\n"
            f"Available stages: {', '.join(_list_contract_ids())}"
        )

    with open(contract_path, encoding="utf-8") as f:
        contract = yaml.safe_load(f)

    if contract is None:
        raise ValueError(f"Contract for '{stage_id}' is empty or unparseable")

    errors = validate_contract(contract)
    if errors:
        raise ValueError(
            f"Contract '{stage_id}' failed schema validation: {'; '.join(errors)}"
        )

    return contract


def _list_contract_ids() -> list[str]:
    """List all available contract stage IDs (without loading full YAML)."""
    ids = []
    for cf in sorted(_CONTRACTS_DIR.glob("*.yaml")):
        ids.append(cf.stem)
    return ids


def list_contracts() -> list[dict]:
    """Load and return all 17 stage execution contracts."""
    contracts = []
    for cid in _list_contract_ids():
        contracts.append(load_contract(cid))
    return contracts


def validate_contract(contract: dict) -> list[str]:
    """Validate a contract dict against stage-execution.schema.json.

    Returns list of error messages (empty = valid).
    """
    schema = _load_schema()
    validator = jsonschema.Draft7Validator(schema)
    return [e.message for e in validator.iter_errors(contract)]


def get_contracts_by_type(executor_type: str) -> list[dict]:
    """Filter contracts by executor_type."""
    return [c for c in list_contracts() if c.get("executor_type") == executor_type]


# ---------------------------------------------------------------------------
# M2.2: Done Conditions Checker
# ---------------------------------------------------------------------------

def _evaluate_condition(condition: str, project_dir: Path) -> bool:
    """Evaluate a single done condition expression.

    Supported expressions:
        file_exists:<path>          - path exists and is non-empty
        record_count:<path> > N     - JSONL line count > N
        record_count:<path> >= N    - JSONL line count >= N
        csv_has_rows:<path>         - CSV has header + at least 1 data row
        no_unresolved_cite_needed:<path>  - no [CITE NEEDED] in markdown
        qa_errors == 0              - QA report has 0 errors (literal)

    Returns True if condition is met, False otherwise.
    """
    condition = condition.strip()

    # file_exists:<path>
    if condition.startswith("file_exists:"):
        rel_path = condition[len("file_exists:"):].strip()
        target = project_dir / rel_path
        if not target.exists():
            return False
        if target.is_file() and target.stat().st_size == 0:
            return False
        if target.is_dir() and not any(target.iterdir()):
            return False
        return True

    # record_count:<path> > N or >= N
    m = re.match(r"record_count:(.+?)\s*(>|>=)\s*(\d+)", condition)
    if m:
        rel_path = m.group(1).strip()
        op = m.group(2)
        threshold = int(m.group(3))
        target = project_dir / rel_path
        if not target.exists():
            return False
        count = _count_jsonl_lines(target)
        if op == ">":
            return count > threshold
        else:  # >=
            return count >= threshold

    # csv_has_rows:<path>
    if condition.startswith("csv_has_rows:"):
        rel_path = condition[len("csv_has_rows:"):].strip()
        target = project_dir / rel_path
        if not target.exists():
            return False
        return _csv_has_data(target)

    # no_unresolved_cite_needed:<path>
    if condition.startswith("no_unresolved_cite_needed:"):
        rel_path = condition[len("no_unresolved_cite_needed:"):].strip()
        target = project_dir / rel_path
        if not target.exists():
            return True  # No file = no cite needed issues
        content = target.read_text(encoding="utf-8", errors="ignore")
        return "[CITE NEEDED]" not in content and "[cite needed]" not in content.lower()

    # qa_errors == 0
    if condition.strip() == "qa_errors == 0":
        # Look for qa-report files in outputs/qa/
        qa_dir = project_dir / "outputs" / "qa"
        if not qa_dir.exists():
            return True  # No QA = no errors
        for qa_file in sorted(qa_dir.glob("qa-report-*.md"), reverse=True):
            content = qa_file.read_text(encoding="utf-8", errors="ignore")
            # Simple heuristic: look for "Errors: N" pattern
            m = re.search(r"\*\*Errors\*\*[:\s]*(\d+)", content)
            if m:
                return int(m.group(1)) == 0
        return True  # Could not parse, assume ok

    raise ValueError(f"Unrecognized condition expression: '{condition}'")


def _count_jsonl_lines(path: Path) -> int:
    """Count non-empty, valid JSON lines in a JSONL file."""
    count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                count += 1
            except json.JSONDecodeError:
                continue
    return count


def _csv_has_data(path: Path) -> bool:
    """Check if a CSV file has at least a header + 1 data row."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        lines = [line.strip() for line in f if line.strip()]
    return len(lines) >= 2  # header + at least one data row


def check_done_conditions(stage_id: str, project_dir: Path) -> tuple[bool, list[str]]:
    """Check if a stage's done conditions are met.

    For script/manual/hybrid stages: checks contract['done_conditions'].
    For skill_handoff stages: checks contract['stage_done'].

    Returns (all_met: bool, unmet_conditions: list[str]).
    """
    contract = load_contract(stage_id)
    executor_type = contract.get("executor_type", "manual")

    if executor_type == "skill_handoff":
        conditions = contract.get("stage_done", [])
    else:
        conditions = contract.get("done_conditions", [])

    if not conditions:
        return True, []

    unmet = []
    for cond in conditions:
        try:
            if not _evaluate_condition(cond, project_dir):
                unmet.append(cond)
        except Exception as e:
            unmet.append(f"{cond} (eval error: {e})")

    return len(unmet) == 0, unmet


def check_handoff_done(stage_id: str, project_dir: Path) -> tuple[bool, list[str]]:
    """Check if a skill_handoff stage's handoff conditions are met.

    Checks contract['handoff_done'] and verifies the handoff JSON file exists.

    Returns (all_met: bool, unmet_conditions: list[str]).
    """
    contract = load_contract(stage_id)
    executor_type = contract.get("executor_type")

    if executor_type != "skill_handoff":
        return True, []

    conditions = contract.get("handoff_done", [])
    if not conditions:
        return True, []

    unmet = []
    for cond in conditions:
        try:
            if not _evaluate_condition(cond, project_dir):
                unmet.append(cond)
        except Exception as e:
            unmet.append(f"{cond} (eval error: {e})")

    return len(unmet) == 0, unmet


# ---------------------------------------------------------------------------
# M2.2: Artifact Logging
# ---------------------------------------------------------------------------

def log_artifacts(
    project_dir: Path,
    stage_id: str,
    artifacts: list[str],
    executor: str,
) -> None:
    """Append an artifact entry to .paper-workflow/artifact-manifest.jsonl.

    Creates the .paper-workflow/ directory if it doesn't exist.
    Uses atomic append (write to temp + rename) for safety.
    """
    pw_dir = project_dir / ".paper-workflow"
    pw_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = pw_dir / "artifact-manifest.jsonl"

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage_id": stage_id,
        "action": "created",
        "artifacts": artifacts,
        "executor": executor,
    }

    with open(manifest_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# M2.3: Stage Executor Stubs
# ---------------------------------------------------------------------------

def _execute_script_stage(
    stage_id: str,
    contract: dict,
    project_dir: Path,
    config: dict,
) -> dict:
    """Execute a script-type stage. STUB in v0.2 — will be implemented in M3."""
    return {
        "executed": False,
        "stage_id": stage_id,
        "executor_type": "script",
        "recommended_status": "in_progress",
        "handoff_generated": False,
        "requires_confirmation": contract.get("user_confirmation_required", False),
        "artifacts": [],
        "warnings": ["[v0.2 stub] script executor not yet implemented"],
        "blocked_reason": None,
    }


def _execute_skill_handoff_stage(
    stage_id: str,
    contract: dict,
    project_dir: Path,
    state: dict,
    config: dict,
) -> dict:
    """Generate a skill handoff task package. STUB in v0.2 — M4 will implement."""
    return {
        "executed": False,
        "stage_id": stage_id,
        "executor_type": "skill_handoff",
        "recommended_status": "waiting_for_user",
        "handoff_generated": True,
        "requires_confirmation": True,
        "artifacts": [],
        "warnings": ["[v0.2 stub] skill_handoff executor not yet implemented"],
        "blocked_reason": None,
    }


def _execute_manual_stage(
    stage_id: str,
    contract: dict,
    project_dir: Path,
) -> dict:
    """Print manual task instructions. STUB in v0.2 — M5 will implement."""
    return {
        "executed": False,
        "stage_id": stage_id,
        "executor_type": "manual",
        "recommended_status": "waiting_for_user",
        "handoff_generated": False,
        "requires_confirmation": True,
        "artifacts": [],
        "warnings": ["[v0.2 stub] manual executor not yet implemented"],
        "blocked_reason": None,
    }


def _execute_hybrid_stage(
    stage_id: str,
    contract: dict,
    project_dir: Path,
    state: dict,
    config: dict,
) -> dict:
    """Run script check then handoff if needed. STUB in v0.2 — M6 will implement."""
    return {
        "executed": False,
        "stage_id": stage_id,
        "executor_type": "hybrid",
        "recommended_status": "in_progress",
        "handoff_generated": False,
        "requires_confirmation": False,
        "artifacts": [],
        "warnings": ["[v0.2 stub] hybrid executor not yet implemented"],
        "blocked_reason": None,
    }


# ---------------------------------------------------------------------------
# M2.3: Main Dispatcher
# ---------------------------------------------------------------------------

def execute_stage(
    stage_id: str,
    project_dir: Path,
    state: dict,
    config: dict,
    *,
    override: bool = False,
) -> dict:
    """Execute a stage by routing to its registered executor type.

    Does NOT write state.yaml — that is commands.py's responsibility (M7).
    Returns a structured result dict with recommended_status.

    Args:
        stage_id: 17-stage identifier.
        project_dir: Paper project root directory.
        state: Full state dict (from load_state).
        config: Config dict (from load_state).
        override: If True, skip dependency checks (passed to executor).

    Returns:
        {
            "executed": bool,
            "stage_id": str,
            "executor_type": str,
            "recommended_status": str,
            "handoff_generated": bool,
            "requires_confirmation": bool,
            "artifacts": list[str],
            "warnings": list[str],
            "blocked_reason": str | None,
        }
    """
    # Load and validate contract
    try:
        contract = load_contract(stage_id)
    except (FileNotFoundError, ValueError) as e:
        return {
            "executed": False,
            "stage_id": stage_id,
            "executor_type": "unknown",
            "recommended_status": "blocked",
            "handoff_generated": False,
            "requires_confirmation": False,
            "artifacts": [],
            "warnings": [],
            "blocked_reason": str(e),
        }

    executor_type = contract.get("executor_type", "manual")

    # Route to executor
    if executor_type == "script":
        return _execute_script_stage(stage_id, contract, project_dir, config)
    elif executor_type == "skill_handoff":
        return _execute_skill_handoff_stage(stage_id, contract, project_dir, state, config)
    elif executor_type == "manual":
        return _execute_manual_stage(stage_id, contract, project_dir)
    elif executor_type == "hybrid":
        return _execute_hybrid_stage(stage_id, contract, project_dir, state, config)
    else:
        return {
            "executed": False,
            "stage_id": stage_id,
            "executor_type": executor_type,
            "recommended_status": "blocked",
            "handoff_generated": False,
            "requires_confirmation": False,
            "artifacts": [],
            "warnings": [],
            "blocked_reason": f"Unknown executor_type: {executor_type}",
        }
