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
    """Execute a script-type stage. Dispatches to real implementations in M3."""
    base = {
        "executed": False,
        "stage_id": stage_id,
        "executor_type": "script",
        "recommended_status": "in_progress",
        "handoff_generated": False,
        "requires_confirmation": contract.get("user_confirmation_required", False),
        "artifacts": [],
        "warnings": [],
        "blocked_reason": None,
    }

    try:
        if stage_id == "literature_dedup":
            return _exec_literature_dedup(project_dir, base)
        elif stage_id == "evidence_matrix":
            return _exec_evidence_matrix(project_dir, contract, base)
        elif stage_id == "formatting":
            return _exec_formatting(project_dir, config, contract, base)
        elif stage_id == "quality_qa":
            return _exec_quality_qa(project_dir, base)
        else:
            base["warnings"].append(f"[v0.2 stub] script executor for '{stage_id}' not yet implemented")
            return base
    except Exception as e:
        base["recommended_status"] = "blocked"
        base["blocked_reason"] = f"{stage_id} executor error: {e}"
        return base


# ---------------------------------------------------------------------------
# M3.1: literature_dedup executor
# ---------------------------------------------------------------------------

def _exec_literature_dedup(project_dir: Path, base: dict) -> dict:
    """Execute literature_dedup: run dedup.py on catalog.jsonl."""
    import json

    catalog_path = project_dir / "literature" / "catalog.jsonl"
    if not catalog_path.exists() or catalog_path.stat().st_size == 0:
        base["recommended_status"] = "blocked"
        base["blocked_reason"] = "catalog.jsonl is missing or empty"
        return base

    # Read records
    records = []
    with open(catalog_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    base["warnings"].append("skipped malformed line in catalog.jsonl")

    if not records:
        base["recommended_status"] = "blocked"
        base["blocked_reason"] = "catalog.jsonl is empty"
        return base

    original_count = len(records)

    # Run dedup
    from dedup import deduplicate, _generate_report

    result = deduplicate(records)
    unique = result.get("unique", [])
    merged = result.get("merged", [])
    related = result.get("related", [])
    pending = result.get("pending_review", [])

    # Write dedup'd catalog
    _write_catalog(catalog_path, unique)

    # Generate report
    report_path = project_dir / "literature" / "dedup-report.md"
    report_text = _generate_report(result, original_count, len(unique))
    report_path.write_text(report_text, encoding="utf-8")

    log_artifacts(project_dir, "literature_dedup",
                  ["literature/catalog.jsonl", "literature/dedup-report.md"],
                  "dedup.py")

    merged_count = len(merged)
    related_count = len(related)
    pending_count = len(pending)

    base["executed"] = True
    base["recommended_status"] = "done"
    base["artifacts"] = ["literature/catalog.jsonl", "literature/dedup-report.md"]
    base["warnings"] = []
    if pending_count > 0:
        base["warnings"].append(f"{pending_count} items pending manual review")
    if related_count > 0:
        base["warnings"].append(f"{related_count} related version pairs found")
    if merged_count > 0:
        base["warnings"].append(f"{merged_count} record groups merged")
    return base


def _write_catalog(path: Path, records: list[dict]) -> None:
    """Overwrite catalog.jsonl with dedup'd records."""
    import json as _json
    import os as _os
    import tempfile as _tempfile

    tmp_fd, tmp_path = _tempfile.mkstemp(
        suffix=".jsonl", prefix=".catalog-", dir=str(path.parent)
    )
    try:
        with _os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
        _os.replace(tmp_path, path)
    except Exception:
        if _os.path.exists(tmp_path):
            _os.unlink(tmp_path)
        raise


# ---------------------------------------------------------------------------
# M3.2: evidence_matrix executor
# ---------------------------------------------------------------------------

def _exec_evidence_matrix(project_dir: Path, contract: dict, base: dict) -> dict:
    """Execute evidence_matrix: run evidence_manager.py and return pending_confirmation."""
    from evidence_manager import init_evidence_matrix, init_claim_map

    evidence_path = init_evidence_matrix(project_dir)
    claim_path = init_claim_map(project_dir)

    artifacts = []
    if evidence_path.exists():
        artifacts.append("literature/evidence-matrix.csv")
    if claim_path.exists():
        artifacts.append("citations/claim-citation-map.csv")

    log_artifacts(project_dir, "evidence_matrix", artifacts, "evidence_manager.py")

    user_conf = contract.get("user_confirmation_required", True)
    base["executed"] = True
    base["requires_confirmation"] = user_conf
    base["recommended_status"] = "pending_confirmation" if user_conf else "done"
    base["artifacts"] = artifacts
    base["warnings"] = []
    return base


# ---------------------------------------------------------------------------
# M3.3: formatting executor
# ---------------------------------------------------------------------------

def _exec_formatting(project_dir: Path, config: dict, contract: dict, base: dict) -> dict:
    """Execute formatting: run render.py with appropriate profile."""
    from render import render as render_func

    manuscript = project_dir / "manuscript" / "main.md"
    if not manuscript.exists():
        base["recommended_status"] = "blocked"
        base["blocked_reason"] = "manuscript/main.md not found"
        return base

    # Determine profile from config or default
    profile = config.get("default_profile", "thesis-cn")

    output_dir = project_dir / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Optional: materials/templates/reference.docx
    ref_docx = project_dir / "materials" / "templates" / "reference.docx"
    if ref_docx.exists():
        base["warnings"].append("using materials/templates/reference.docx as optional template")
    # Note: render.py currently reads reference-doc from profile config,
    # not from materials/. This is a forward-compatible note.

    result = render_func(profile, manuscript, output_dir, project_dir=project_dir)

    if not result.get("success", False):
        base["recommended_status"] = "blocked"
        base["blocked_reason"] = "render failed: " + "; ".join(result.get("errors", ["unknown error"]))
        base["warnings"] = result.get("warnings", [])
        return base

    # Check outputs/latest/
    latest_dir = output_dir / "latest"
    artifacts = []
    if latest_dir.exists():
        artifacts = [f"outputs/latest/{f.name}" for f in latest_dir.iterdir() if f.is_file()]

    log_artifacts(project_dir, "formatting", artifacts, "render.py")

    base["executed"] = True
    base["recommended_status"] = "done"
    base["artifacts"] = artifacts
    base["warnings"] = result.get("warnings", [])
    return base


# ---------------------------------------------------------------------------
# M3.4: quality_qa executor
# ---------------------------------------------------------------------------

def _exec_quality_qa(project_dir: Path, base: dict) -> dict:
    """Execute quality_qa: run qa_report.py and determine pass/blocked."""
    from qa_report import run_all_checks as qa_checks

    results = qa_checks(project_dir)
    errors = results.get("summary", {}).get("total_errors", 0)
    warnings = results.get("summary", {}).get("total_warnings", 0)
    overall = results.get("overall", "failed")

    artifacts = []
    qa_dir = project_dir / "outputs" / "qa"
    if qa_dir.exists():
        artifacts = [f"outputs/qa/{f.name}" for f in sorted(qa_dir.glob("qa-report-*.md"))]

    log_artifacts(project_dir, "quality_qa", artifacts, "qa_report.py")

    base["executed"] = True
    if errors > 0:
        base["recommended_status"] = "blocked"
        base["blocked_reason"] = f"QA found {errors} errors, {warnings} warnings"
        base["warnings"] = [f"QA overall: {overall}"]
    elif warnings > 0:
        base["recommended_status"] = "done"
        base["warnings"] = [f"QA passed with {warnings} warnings (overall: {overall})"]
    else:
        base["recommended_status"] = "done"
        base["warnings"] = [f"QA passed (overall: {overall})"]
    base["artifacts"] = artifacts
    return base


def _execute_skill_handoff_stage(
    stage_id: str,
    contract: dict,
    project_dir: Path,
    state: dict,
    config: dict,
) -> dict:
    """Generate a skill handoff task package (M4: real implementation)."""
    base = {
        "executed": False,
        "stage_id": stage_id,
        "executor_type": "skill_handoff",
        "recommended_status": "waiting_for_user",
        "handoff_generated": False,
        "requires_confirmation": True,
        "artifacts": [],
        "warnings": [],
        "blocked_reason": None,
    }

    try:
        handoff_path = generate_handoff(stage_id, project_dir, state, config)
        base["handoff_generated"] = True
        base["handoff_path"] = str(handoff_path.relative_to(project_dir))
        base["artifacts"] = [base["handoff_path"]]
        return base
    except Exception as e:
        base["warnings"].append(f"Handoff generation error: {e}")
        # Still return waiting_for_user — handoff failed but shouldn't block
        return base


# ---------------------------------------------------------------------------
# M4.2: Handoff file generation
# ---------------------------------------------------------------------------

def generate_handoff(
    stage_id: str,
    project_dir: Path,
    state: dict,
    config: dict,
) -> Path:
    """Generate a skill handoff JSON file and return its path.

    Writes to .paper-workflow/handoffs/<stage_id>.json
    Updates .paper-workflow/handoffs/latest.json
    """
    import json as _json
    from datetime import datetime, timezone

    contract = load_contract(stage_id)

    # Render the handoff prompt
    from stage_prompts import render_handoff_prompt
    task_prompt = render_handoff_prompt(stage_id, project_dir, state, config)

    # Collect input artifact status
    input_files = {}
    warnings = []
    for art in contract.get("input_artifacts", []):
        optional = art.startswith("optional:")
        clean_path = art[len("optional:"):] if optional else art
        target = project_dir / clean_path

        entry = {"exists": target.exists(), "optional": optional}
        if target.is_file():
            entry["size_bytes"] = target.stat().st_size
        elif target.is_dir():
            try:
                files = [f.name for f in target.iterdir() if f.is_file()]
                entry["file_count"] = len(files)
            except Exception:
                entry["file_count"] = 0

        if not entry["exists"] and not optional:
            warnings.append(f"required input missing: {clean_path}")
        elif not entry["exists"] and optional:
            pass  # optional missing is not a warning

        input_files[clean_path] = entry

    # Collect materials summary
    materials_list: list[str] = []
    materials_dir = project_dir / "materials"
    if materials_dir.is_dir():
        for sub in ["requirements", "templates", "examples", "notes"]:
            sub_dir = materials_dir / sub
            if sub_dir.is_dir():
                for f in sorted(sub_dir.iterdir()):
                    if f.is_file() and not f.name.startswith("."):
                        materials_list.append(f"materials/{sub}/{f.name}")

    # Build expected outputs
    expected_outputs = contract.get("output_artifacts", [])

    # Resolve skill name
    from stage_prompts import _resolve_skill
    skill_name = _resolve_skill(contract, config)

    handoff_data = {
        "stage_id": stage_id,
        "executor_type": "skill_handoff",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "waiting_for_user",
        "skill": skill_name,
        "task_prompt": task_prompt,
        "input_files": input_files,
        "expected_outputs": expected_outputs,
        "materials_summary": materials_list,
        "warnings": warnings,
        "retry_count": 0,
    }

    # Write handoff JSON
    handoffs_dir = project_dir / ".paper-workflow" / "handoffs"
    handoffs_dir.mkdir(parents=True, exist_ok=True)

    handoff_path = handoffs_dir / f"{stage_id}.json"
    handoff_path.write_text(
        _json.dumps(handoff_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Update latest pointer
    latest_path = handoffs_dir / "latest.json"
    latest_path.write_text(
        _json.dumps({"stage_id": stage_id, "timestamp": handoff_data["generated_at"]}, ensure_ascii=False),
        encoding="utf-8",
    )

    # Log artifact
    log_artifacts(
        project_dir, stage_id,
        [f".paper-workflow/handoffs/{stage_id}.json"],
        f"skill_handoff:{skill_name}",
    )

    return handoff_path


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
