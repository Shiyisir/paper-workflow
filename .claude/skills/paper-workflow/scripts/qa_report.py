#!/usr/bin/env python3
"""Unified QA report — integrates all validators into a single report.

Usage:
    python scripts/qa_report.py --project /path/to/project
    python scripts/qa_report.py --project /path/to/project --output outputs/qa
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_catalog import validate_catalog
from validate_citations import (
    check_citekey_consistency,
    check_duplicate_citekeys_wrapper,
    cross_check_citations,
    find_cite_needed,
)
from validate_manuscript import validate_manuscript


def _find_project_root() -> Path:
    current = Path.cwd().resolve()
    for _ in range(10):
        if (current / ".paper-workflow").is_dir():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise FileNotFoundError("找不到 .paper-workflow/ 目录。")


def run_all_checks(project_dir: Path) -> dict:
    """Run all QA checks on a project. Returns structured results.

    Returns:
        {
            "overall": "passed" | "passed_with_warnings" | "failed",
            "timestamp": str,
            "checks": {
                "catalog": {...},
                "citations": {...},
                "manuscript": {...},
                "docx": {...} | None,
                "tex": {...} | None,
            },
            "summary": {"total_errors": int, "total_warnings": int, "checks_run": int},
        }
    """
    results: dict = {
        "overall": "passed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "summary": {"total_errors": 0, "total_warnings": 0, "checks_run": 0},
    }

    # 1. Catalog validation
    results["checks"]["catalog"] = _check_catalog(project_dir)

    # 2. Citation validation
    results["checks"]["citations"] = _check_citations(project_dir)

    # 3. Manuscript validation
    results["checks"]["manuscript"] = _check_manuscript(project_dir)

    # 4. Docx validation (if outputs exist)
    results["checks"]["docx"] = _check_docx(project_dir)

    # 5. Tex validation (if outputs exist)
    results["checks"]["tex"] = _check_tex(project_dir)

    # Compute summary
    total_errors = 0
    total_warnings = 0
    checks_run = 0
    has_error = False
    has_warning = False

    for check_name, check in results["checks"].items():
        if check is None:
            continue
        checks_run += 1
        total_errors += check.get("error_count", 0)
        total_warnings += check.get("warning_count", 0)
        if check.get("error_count", 0) > 0:
            has_error = True
        if check.get("warning_count", 0) > 0:
            has_warning = True

    results["summary"] = {
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "checks_run": checks_run,
    }

    if has_error:
        results["overall"] = "failed"
    elif has_warning:
        results["overall"] = "passed_with_warnings"
    else:
        results["overall"] = "passed"

    return results


def _check_catalog(project_dir: Path) -> dict:
    try:
        result = validate_catalog(project_dir)
        return {
            "status": "passed" if not result["errors"] else "failed",
            "error_count": len(result["errors"]),
            "warning_count": len(result["warnings"]),
            "errors": result["errors"],
            "warnings": result["warnings"],
            "details": f"{result['total_records']} 条文献记录",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_count": 1,
            "warning_count": 0,
            "errors": [str(e)],
            "warnings": [],
            "details": "check failed",
        }


def _check_citations(project_dir: Path) -> dict:
    errors = []
    warnings = []
    ms_path = project_dir / "manuscript" / "main.md"
    bib_path = project_dir / "literature" / "references.bib"
    claim_path = project_dir / "citations" / "claim-citation-map.csv"

    if not ms_path.exists():
        return {
            "status": "skipped", "error_count": 0, "warning_count": 0,
            "errors": [], "warnings": [], "details": "manuscript/main.md 不存在",
        }

    # Citekey consistency
    if bib_path.exists():
        try:
            cons = check_citekey_consistency(ms_path, bib_path)
            if cons["missing_in_bib"]:
                errors.append(f"missing_in_bib: {', '.join(cons['missing_in_bib'])}")
            if cons["unused_in_text"]:
                warnings.append(f"unused_in_text: {', '.join(cons['unused_in_text'][:10])}")
        except Exception as e:
            errors.append(f"citekey consistency check failed: {e}")

        # Duplicate citekeys
        try:
            dupes = check_duplicate_citekeys_wrapper(bib_path)
            if dupes:
                errors.append(f"duplicate citekeys: {', '.join(dupes)}")
        except Exception:
            pass

    # [CITE NEEDED]
    try:
        cn = find_cite_needed(ms_path)
        if cn:
            warnings.append(f"[CITE NEEDED]: {len(cn)} 处 (行 {', '.join(str(c['line']) for c in cn[:5])})")
    except Exception:
        pass

    # Cross-check with claim map
    if claim_path.exists():
        try:
            cross = cross_check_citations(ms_path, claim_path)
            if cross["in_manuscript_not_in_claim_map"]:
                warnings.append(f"evidence gap: {', '.join(cross['in_manuscript_not_in_claim_map'])}")
        except Exception:
            pass

    return {
        "status": "passed" if not errors else "failed",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "details": f"{len(errors)} errors, {len(warnings)} warnings",
    }


def _check_manuscript(project_dir: Path) -> dict:
    ms_path = project_dir / "manuscript" / "main.md"
    if not ms_path.exists():
        return {
            "status": "skipped", "error_count": 0, "warning_count": 0,
            "errors": [], "warnings": [], "details": "manuscript/main.md 不存在",
        }
    try:
        result = validate_manuscript(ms_path, project_dir)
        return {
            "status": "passed" if not result["has_errors"] else "failed",
            "error_count": len(result["errors"]),
            "warning_count": len(result["warnings"]),
            "errors": result["errors"],
            "warnings": result["warnings"],
            "details": str(result["summary"]),
        }
    except Exception as e:
        return {
            "status": "error", "error_count": 1, "warning_count": 0,
            "errors": [str(e)], "warnings": [], "details": "check failed",
        }


def _check_docx(project_dir: Path) -> dict | None:
    output_dir = project_dir / "outputs"
    docx_files = list(output_dir.glob("*.docx"))
    if not docx_files:
        return None  # No docx outputs

    errors = []
    warnings = []
    try:
        from validate_docx import validate_docx
        for df in docx_files[-3:]:  # Check last 3
            r = validate_docx(df)
            errors.extend(r["errors"])
            warnings.extend(r["warnings"])
    except ImportError:
        return {
            "status": "skipped", "error_count": 0, "warning_count": 1,
            "errors": [], "warnings": ["python-docx 未安装, 跳过 docx 检查"],
            "details": f"{len(docx_files)} docx files found",
        }
    except Exception as e:
        errors.append(str(e))

    return {
        "status": "passed" if not errors else "failed",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "details": f"{len(docx_files)} docx files checked",
    }


def _check_tex(project_dir: Path) -> dict | None:
    output_dir = project_dir / "outputs"
    tex_files = list(output_dir.glob("*.tex"))
    if not tex_files:
        return None

    errors = []
    warnings = []
    try:
        from validate_tex import validate_tex
        for tf in tex_files[-3:]:
            r = validate_tex(tf, project_dir)
            errors.extend(r["errors"])
            warnings.extend(r["warnings"])
    except Exception as e:
        errors.append(str(e))

    return {
        "status": "passed" if not errors else "failed",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "details": f"{len(tex_files)} tex files checked",
    }


def _next_report_version(qa_dir: Path) -> Path:
    """Find next QA report version number."""
    qa_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(r"qa-report-v(\d{3})\.md$")
    max_ver = 0
    for f in qa_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            max_ver = max(max_ver, int(m.group(1)))
    return qa_dir / f"qa-report-v{max_ver + 1:03d}.md"


def generate_qa_report(results: dict, output_path: Path) -> Path:
    """Write QA results as a Markdown report."""
    lines = [
        "# QA 质量核验报告",
        "",
        f"**生成时间**: {results['timestamp'][:19]}",
        f"**总体状态**: {_status_icon(results['overall'])} {results['overall']}",
        "",
        "## 摘要",
        "",
        f"| 指标 | 值 |",
        f"|------|----|",
        f"| 检查项 | {results['summary']['checks_run']} |",
        f"| Errors | {results['summary']['total_errors']} |",
        f"| Warnings | {results['summary']['total_warnings']} |",
        f"| 总体结果 | {_status_icon(results['overall'])} {results['overall']} |",
        "",
    ]

    for check_name, check in results["checks"].items():
        if check is None:
            lines.append(f"## {check_name}: ⏭ skipped")
            lines.append("")
            continue

        icon = _status_icon(check.get("status", "unknown"))
        lines.append(f"## {check_name}: {icon} {check.get('status', '?')}")
        lines.append(f"  {check.get('details', '')}")
        lines.append("")

        for err in check.get("errors", []):
            lines.append(f"  - ❌ {err}")
        for warn in check.get("warnings", []):
            lines.append(f"  - ⚠ {warn}")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def _status_icon(status: str) -> str:
    icons = {"passed": "✅", "passed_with_warnings": "⚠", "failed": "❌", "skipped": "⏭", "error": "💥"}
    return icons.get(status, "❓")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run unified QA checks")
    parser.add_argument("--project", help="Paper project root directory")
    parser.add_argument("--output", help="QA report output directory (default: outputs/qa)")
    args = parser.parse_args()

    project_dir = Path(args.project) if args.project else _find_project_root()
    results = run_all_checks(project_dir)

    # Print summary
    print(f"QA 报告: {results['overall']}")
    print(f"  Errors: {results['summary']['total_errors']}")
    print(f"  Warnings: {results['summary']['total_warnings']}")
    print(f"  Checks: {results['summary']['checks_run']}")

    # Generate report
    qa_dir = Path(args.output) if args.output else (project_dir / "outputs" / "qa")
    report_path = _next_report_version(qa_dir)
    generate_qa_report(results, report_path)
    print(f"\n报告: {report_path}")

    return 1 if results["overall"] == "failed" else 0


if __name__ == "__main__":
    sys.exit(main())
