#!/usr/bin/env python3
"""Check environment for paper-workflow MVP.

Outputs a JSON environment report to stdout.
Exit code 0 means all essentials are available.
Exit code 1 means one or more essentials are missing (warnings only → still 0).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def check_python() -> dict:
    """Check Python version."""
    major, minor, micro = sys.version_info[:3]
    ok = (major, minor) >= (3, 10)
    return {
        "python_version": f"{major}.{minor}.{micro}",
        "status": "ok" if ok else "error",
        "message": None if ok else "Python >= 3.10 required",
    }


def check_dependency(name: str, import_name: str | None = None) -> dict:
    """Check if a Python package is importable."""
    if import_name is None:
        import_name = name.replace("-", "_")
    try:
        __import__(import_name)
        return {"package": name, "status": "ok"}
    except ImportError:
        return {"package": name, "status": "error", "message": f"pip install {name}"}


def check_dependencies() -> list[dict]:
    """Check all required Python packages."""
    deps = [
        ("yaml", "yaml"),           # pyyaml
        ("jsonschema", "jsonschema"),
        ("docx", "docx"),           # python-docx
        ("lxml", "lxml"),
        ("bibtexparser", "bibtexparser"),
    ]
    results = []
    for import_name, pkg_name in deps:
        results.append(check_dependency(pkg_name, import_name))
    return results


def check_pandoc() -> dict:
    """Check Pandoc availability and --citeproc support."""
    pandoc_path = shutil.which("pandoc")
    if not pandoc_path:
        return {
            "pandoc": {
                "status": "error",
                "path": None,
                "version": None,
                "citeproc": None,
                "message": "Pandoc not found in PATH. Install from https://pandoc.org",
            }
        }

    try:
        result = subprocess.run(
            [pandoc_path, "--version"], capture_output=True, text=True, timeout=10
        )
        version_line = result.stdout.strip().split("\n")[0]
    except Exception:
        version_line = "unknown"

    # Test --citeproc flag (built-in filter, not external pandoc-citeproc)
    citeproc_ok = False
    try:
        # Use --citeproc on a minimal input to verify the filter works
        test_result = subprocess.run(
            [pandoc_path, "--citeproc", "--to", "plain", "--csl", "about:blank"],
            input="---\nreferences: []\n---\n\ntest\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        # about:blank CSL will likely error, but the --citeproc flag itself should be recognized
        citeproc_ok = "--citeproc" in str(test_result.stderr) or test_result.returncode in (0, 3, 4, 6, 23, 31, 33, 34, 43, 63, 64, 99)
        # More robust: just check if pandoc accepts the --citeproc flag
        flag_test = subprocess.run(
            [pandoc_path, "--citeproc", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        citeproc_ok = flag_test.returncode == 0
    except Exception:
        # Fallback: check help output
        try:
            help_result = subprocess.run(
                [pandoc_path, "--help"], capture_output=True, text=True, timeout=5
            )
            citeproc_ok = "--citeproc" in help_result.stdout
        except Exception:
            pass

    # Also check for legacy pandoc-citeproc as fallback
    legacy_citeproc = shutil.which("pandoc-citeproc")
    if legacy_citeproc:
        try:
            subprocess.run([legacy_citeproc, "--version"], capture_output=True, timeout=5)
        except Exception:
            legacy_citeproc = None

    return {
        "pandoc": {
            "status": "ok",
            "path": pandoc_path,
            "version": version_line,
            "citeproc_builtin": citeproc_ok,
            "citeproc_legacy": legacy_citeproc is not None,
            "message": None,
        }
    }


def check_latex() -> dict:
    """Check LaTeX engine availability."""
    engines = {}
    for engine in ["xelatex", "pdflatex", "lualatex"]:
        path = shutil.which(engine)
        engines[engine] = {
            "available": path is not None,
            "path": path,
        }

    any_available = any(e["available"] for e in engines.values())
    return {
        "latex": {
            "status": "ok" if any_available else "warning",
            "engines": engines,
            "message": None if any_available else "No LaTeX engine found. LaTeX rendering will be unavailable.",
        }
    }


def check_svg_tools() -> dict:
    """Check SVG conversion tool availability."""
    cairosvg_available = False
    try:
        import cairosvg  # noqa: F401
        cairosvg_available = True
    except ImportError:
        pass

    rsvg_available = shutil.which("rsvg-convert") is not None

    any_available = cairosvg_available or rsvg_available
    return {
        "svg_conversion": {
            "status": "ok" if any_available else "warning",
            "cairosvg": cairosvg_available,
            "rsvg_convert": rsvg_available,
            "message": None if any_available else "No SVG converter found. SVG-to-PNG/PDF will be unavailable.",
        }
    }


def main():
    results = {
        "paper_workflow_env": {
            "python": check_python(),
            "dependencies": check_dependencies(),
            "pandoc": check_pandoc()["pandoc"],
            "latex": check_latex()["latex"],
            "svg_conversion": check_svg_tools()["svg_conversion"],
        }
    }

    # Determine overall status
    has_error = (
        results["paper_workflow_env"]["python"]["status"] == "error"
        or results["paper_workflow_env"]["pandoc"]["status"] == "error"
        or any(d["status"] == "error" for d in results["paper_workflow_env"]["dependencies"])
    )

    results["paper_workflow_env"]["_overall"] = "error" if has_error else "ok"

    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 1 if has_error else 0


if __name__ == "__main__":
    sys.exit(main())
