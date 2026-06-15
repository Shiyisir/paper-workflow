#!/usr/bin/env python3
"""Render Markdown manuscript to docx/tex/md.

Usage:
    python scripts/render.py --profile thesis-cn --input manuscript/main.md --output-dir outputs
    python scripts/render.py --profile thesis-cn --input manuscript/main.md --output-dir outputs --dry-run
    python scripts/render.py --profile markdown-draft --input manuscript/main.md --output-dir outputs
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_manuscript import validate_manuscript

SKILL_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = SKILL_DIR / "templates" / "profiles"


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


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------

def load_profile(profile_name: str) -> dict:
    """Load a render profile from templates/profiles/<name>.yaml."""
    profile_path = PROFILES_DIR / f"{profile_name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(f"Profile 不存在: {profile_path}")
    with open(profile_path, encoding="utf-8") as f:
        profile = yaml.safe_load(f)
    if not isinstance(profile, dict):
        raise ValueError(f"Profile 格式无效: {profile_path}")
    return profile


# ---------------------------------------------------------------------------
# Versioned output
# ---------------------------------------------------------------------------

def _stem_from_profile(profile_name: str) -> str:
    """Get output file stem from profile name."""
    stems = {
        "thesis-cn": "thesis-cn",
        "course-cn": "course-cn",
        "journal-word": "journal-word",
        "journal-latex": "manuscript",
        "markdown-draft": "draft",
    }
    return stems.get(profile_name, profile_name)


def next_output_version(output_dir: Path, stem: str, suffix: str) -> Path:
    """Find next version number and return output path.

    Scans output_dir for <stem>-v<NNN>.<suffix> and returns v001, v002, etc.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"{re.escape(stem)}-v(\d{{3}})\.{re.escape(suffix)}$")
    max_ver = 0
    for f in output_dir.iterdir():
        m = pattern.match(f.name)
        if m:
            max_ver = max(max_ver, int(m.group(1)))
    next_ver = max_ver + 1
    return output_dir / f"{stem}-v{next_ver:03d}.{suffix}"


# ---------------------------------------------------------------------------
# Pandoc command builder
# ---------------------------------------------------------------------------

def build_pandoc_command(
    profile: dict,
    input_md: Path,
    output_path: Path,
    project_dir: Path,
) -> list[str]:
    """Build pandoc command from profile and paths."""
    output_fmt = profile.get("output", "docx")

    cmd = ["pandoc", str(input_md)]

    # Output format
    if output_fmt == "docx":
        cmd.extend(["--to", "docx"])
    elif output_fmt == "tex":
        cmd.extend(["--to", "latex"])
    else:
        raise ValueError(f"Unsupported output format for pandoc: {output_fmt}")

    cmd.extend(["--output", str(output_path)])

    # Smart quotes etc.
    cmd.extend(["--from", "markdown+smart"])

    # Section numbering
    if profile.get("number_sections"):
        cmd.append("--number-sections")

    # Table of contents
    if profile.get("toc"):
        cmd.extend(["--toc", f"--toc-depth={profile.get('toc_depth', 3)}"])

    # Reference doc
    ref_doc = profile.get("reference_doc")
    if ref_doc and output_fmt == "docx":
        ref_path = (SKILL_DIR / ref_doc).resolve() if not Path(ref_doc).is_absolute() else Path(ref_doc)
        if ref_path.exists():
            cmd.extend(["--reference-doc", str(ref_path)])

    # CSL and bibliography
    csl = profile.get("csl")
    bib_path = project_dir / "literature" / "references.bib"
    if csl and bib_path.exists():
        csl_path = (SKILL_DIR / csl).resolve() if not Path(csl).is_absolute() else Path(csl)
        if csl_path.exists():
            cmd.extend(["--csl", str(csl_path)])
            cmd.extend(["--bibliography", str(bib_path)])
            cmd.append("--citeproc")

    # LaTeX template
    latex_tpl = profile.get("latex_template")
    if latex_tpl and output_fmt == "tex":
        tpl_path = (SKILL_DIR / latex_tpl).resolve() if not Path(latex_tpl).is_absolute() else Path(latex_tpl)
        if tpl_path.exists():
            cmd.extend(["--template", str(tpl_path)])

    # Wrap
    cmd.append("--wrap=preserve")

    return cmd


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(
    profile_name: str,
    input_md: Path,
    output_dir: Path,
    project_dir: Path | None = None,
    dry_run: bool = False,
) -> dict:
    """Render a manuscript using the given profile.

    Returns:
        {
            "success": bool,
            "profile": str,
            "output_path": Path | None,
            "version": str,
            "dry_run": bool,
            "operations": [str],       # planned/executed ops
            "errors": [str],
            "warnings": [str],
        }
    """
    project_dir = project_dir or _find_project_root()
    profile = load_profile(profile_name)
    output_fmt = profile.get("output", "docx")

    operations: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Pre-render validation
    operations.append("validate_manuscript")
    if not dry_run:
        validation = validate_manuscript(input_md, profile=profile_name)
        if validation["has_errors"]:
            errors.extend(validation["errors"])
            return {
                "success": False, "profile": profile_name, "output_path": None,
                "version": "", "dry_run": dry_run,
                "operations": operations, "errors": errors,
                "warnings": warnings + validation["warnings"],
            }
        warnings.extend(validation["warnings"])

    # 2. Determine output
    stem = _stem_from_profile(profile_name)
    suffix_map = {"docx": "docx", "tex": "tex", "md": "md"}
    suffix = suffix_map.get(output_fmt, output_fmt)

    if not dry_run:
        output_path = next_output_version(output_dir, stem, suffix)
    else:
        output_path = output_dir / f"{stem}-vDRY.{suffix}"

    operations.append(f"output → {output_path.name}")

    # 3. Render
    if output_fmt == "md":
        # markdown-draft: just copy or pass through
        operations.append("copy markdown (no pandoc)")
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_md, output_path)
    else:
        # pandoc
        cmd = build_pandoc_command(profile, input_md, output_path, project_dir)
        operations.append(f"pandoc: {' '.join(cmd[:6])}...")

        if not dry_run:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                errors.append(f"Pandoc 失败 (rc={result.returncode}): {result.stderr[:500]}")
                return {
                    "success": False, "profile": profile_name,
                    "output_path": output_path, "version": output_path.stem,
                    "dry_run": dry_run, "operations": operations,
                    "errors": errors, "warnings": warnings,
                }

    # 4. Copy to latest if no errors
    if not dry_run and not errors:
        latest_dir = output_dir / "latest"
        latest_dir.mkdir(parents=True, exist_ok=True)
        latest_file = latest_dir / f"{stem}.{suffix}"
        shutil.copy2(output_path, latest_file)
        operations.append(f"latest → {latest_file.name}")

    return {
        "success": True,
        "profile": profile_name,
        "output_path": output_path if not dry_run else None,
        "version": output_path.stem if not dry_run else "(dry-run)",
        "dry_run": dry_run,
        "operations": operations,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Render manuscript with profile")
    parser.add_argument("--profile", required=True, help="Profile name (e.g., thesis-cn)")
    parser.add_argument("--input", required=True, help="Path to Markdown manuscript")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--project", help="Paper project root directory")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no file creation")
    args = parser.parse_args()

    project_dir = Path(args.project) if args.project else _find_project_root()

    result = render(
        args.profile,
        Path(args.input),
        Path(args.output_dir),
        project_dir,
        args.dry_run,
    )

    # Print operations
    print(f"Profile: {result['profile']}  |  {'DRY-RUN' if result['dry_run'] else 'RENDER'}")
    print(f"版本: {result['version']}")
    print()
    for op in result["operations"]:
        print(f"  → {op}")

    if result["errors"]:
        print(f"\n错误 ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  ❌ {e}")

    if result["warnings"]:
        print(f"\n警告 ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"  ⚠ {w}")

    if result["success"] and not result["dry_run"]:
        print(f"\n✓ 输出: {result['output_path']}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
