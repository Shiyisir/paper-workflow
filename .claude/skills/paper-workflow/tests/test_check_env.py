"""Test check_env.py output format and expected fields."""

import json
import subprocess
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
CHECK_ENV = SCRIPTS_DIR / "check_env.py"


def test_check_env_runs():
    """check_env.py can be invoked and produces valid JSON."""
    result = subprocess.run(
        [sys.executable, str(CHECK_ENV)],
        capture_output=True, text=True, timeout=30,
    )
    # Exit code should be 0 or 1 (both are valid — 1 means warnings)
    assert result.returncode in (0, 1), f"stderr: {result.stderr}"

    data = json.loads(result.stdout)
    assert "paper_workflow_env" in data

    env = data["paper_workflow_env"]
    assert "_overall" in env
    assert env["_overall"] in ("ok", "error")


def test_check_env_has_required_sections():
    """check_env.py output contains all required sections."""
    result = subprocess.run(
        [sys.executable, str(CHECK_ENV)],
        capture_output=True, text=True, timeout=30,
    )
    data = json.loads(result.stdout)
    env = data["paper_workflow_env"]

    required = ["python", "dependencies", "pandoc", "latex", "svg_conversion"]
    for section in required:
        assert section in env, f"Missing section: {section}"


def test_python_section():
    """Python section reports version and status."""
    result = subprocess.run(
        [sys.executable, str(CHECK_ENV)],
        capture_output=True, text=True, timeout=30,
    )
    data = json.loads(result.stdout)
    python = data["paper_workflow_env"]["python"]

    assert "python_version" in python
    assert python["status"] == "ok"


def test_pandoc_section():
    """Pandoc section reports path and citeproc support."""
    result = subprocess.run(
        [sys.executable, str(CHECK_ENV)],
        capture_output=True, text=True, timeout=30,
    )
    data = json.loads(result.stdout)
    pandoc = data["paper_workflow_env"]["pandoc"]

    assert "status" in pandoc
    assert "citeproc_builtin" in pandoc
    # If pandoc is available, path should be non-None
    if pandoc["status"] == "ok":
        assert pandoc["path"] is not None


def test_dependencies_all_ok():
    """All required dependencies are installed."""
    result = subprocess.run(
        [sys.executable, str(CHECK_ENV)],
        capture_output=True, text=True, timeout=30,
    )
    data = json.loads(result.stdout)
    deps = data["paper_workflow_env"]["dependencies"]

    for dep in deps:
        assert dep["status"] == "ok", f"Dependency {dep['package']} is missing"
