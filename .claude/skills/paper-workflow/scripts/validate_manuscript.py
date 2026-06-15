#!/usr/bin/env python3
"""Validate Markdown manuscript structure, formulas, and attachments.

Usage:
    python scripts/validate_manuscript.py manuscript/main.md
    python scripts/validate_manuscript.py manuscript/main.md --profile docx-safe
"""

import argparse
import re
import sys
from pathlib import Path

UNICODE_SUBSCRIPTS = re.compile(r"[₀-₉₊₋₌₍₎]")
TAG_PATTERN = re.compile(r"\\tag\{")
CITE_NEEDED_PATTERN = re.compile(r"\[CITE\s*NEEDED\]", re.IGNORECASE)
IMAGE_PATTERN = re.compile(r"!\[.*?\]\((.*?)\)")
FIGURE_NUM_PATTERN = re.compile(r"(?:图|Figure|Fig\.?)\s*(\d+)", re.IGNORECASE)
TABLE_NUM_PATTERN = re.compile(r"(?:表|Table)\s*(\d+)", re.IGNORECASE)
HEADING_PATTERN = re.compile(r"^(#{1,6})\s", re.MULTILINE)
DOLLAR_MATH_PATTERN = re.compile(r"(?<!\$)\$[^$]+\$(?!\$)")
DISPLAY_MATH_START = re.compile(r"(?<!\$)\$\$")


def validate_structure(md_path: Path) -> dict:
    """Check heading hierarchy, figure/table numbering, and [CITE NEEDED]."""
    errors: list[str] = []
    warnings: list[str] = []

    if not md_path.exists():
        return {"errors": [f"文件不存在: {md_path}"], "warnings": [], "summary": "文件缺失"}

    text = md_path.read_text(encoding="utf-8")

    # Heading levels
    headings = []
    for m in HEADING_PATTERN.finditer(text):
        level = len(m.group(1))
        line_num = text[:m.start()].count("\n") + 1
        headings.append((level, line_num))

    for i in range(1, len(headings)):
        prev_level, _ = headings[i - 1]
        curr_level, curr_line = headings[i]
        if curr_level > prev_level + 1:
            errors.append(
                f"第 {curr_line} 行: 标题层级跳跃 (#{'#' * prev_level} → #{'#' * curr_level})"
            )

    # Figure numbering
    fig_nums = [int(m.group(1)) for m in FIGURE_NUM_PATTERN.finditer(text)]
    if fig_nums:
        if sorted(fig_nums) != list(range(min(fig_nums), max(fig_nums) + 1)):
            errors.append("图表编号不连续或有重复")
        if len(set(fig_nums)) != len(fig_nums):
            errors.append("图表编号存在重复")

    # Table numbering
    tbl_nums = [int(m.group(1)) for m in TABLE_NUM_PATTERN.finditer(text)]
    if tbl_nums:
        if len(set(tbl_nums)) != len(tbl_nums):
            errors.append("表格编号存在重复")

    # [CITE NEEDED]
    cn_matches = list(CITE_NEEDED_PATTERN.finditer(text))
    if cn_matches:
        lines = sorted({text[:m.start()].count("\n") + 1 for m in cn_matches})
        warnings.append(f"发现 {len(cn_matches)} 处 [CITE NEEDED]: 第 {', '.join(map(str, lines))} 行")

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": f"检查: {len(headings)} 个标题, {len(fig_nums)} 个图号, {len(tbl_nums)} 个表号, {len(cn_matches)} 处 CITE_NEEDED",
    }


def validate_formulas(md_path: Path, profile: str | None = None) -> dict:
    """Check formula syntax and profile-specific risks."""
    errors: list[str] = []
    warnings: list[str] = []

    if not md_path.exists():
        return {"errors": [f"文件不存在: {md_path}"], "warnings": [], "summary": "文件缺失"}

    text = md_path.read_text(encoding="utf-8")

    # $$ pair check
    dollar_dollar_count = len(re.findall(r"(?<!\$)\$\$(?!\$)", text))
    if dollar_dollar_count % 2 != 0:
        errors.append("$$ 公式块不成对")

    # Unicode subscripts
    us_matches = list(UNICODE_SUBSCRIPTS.finditer(text))
    if us_matches:
        lines = sorted({text[:m.start()].count("\n") + 1 for m in us_matches})
        warnings.append(
            f"发现 Unicode 下标字符（可能导致 Arial 缺字），请用 $n_1$ 替换: "
            f"第 {', '.join(map(str, lines[:5]))} 行{'...' if len(lines) > 5 else ''}"
        )

    # \tag{} in docx-safe profile
    tag_matches = list(TAG_PATTERN.finditer(text))
    if tag_matches and profile in ("docx-safe", "thesis-cn", "course-cn"):
        lines = sorted({text[:m.start()].count("\n") + 1 for m in tag_matches})
        warnings.append(
            f"docx profile 下 \\tag{{}} 可能导致 Pandoc OMML 转换失败: "
            f"第 {', '.join(map(str, lines[:5]))} 行{'...' if len(lines) > 5 else ''}"
        )

    # $ pairing (heuristic: odd count may indicate problem)
    single_dollar = len(re.findall(r"(?<!\$)\$(?!\$)", text))
    if single_dollar % 2 != 0:
        warnings.append(f"行内 $ 数量为奇数 ({single_dollar} 个)，可能存在未闭合的行内公式")

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": f"检查: $$ {'成对' if dollar_dollar_count % 2 == 0 else '不成对'}, "
                   f"{len(us_matches)} 处 Unicode 下标, {len(tag_matches)} 处 \\tag",
    }


def validate_attachments(md_path: Path, base_dir: Path) -> dict:
    """Check that image references in Markdown point to existing files."""
    errors: list[str] = []
    warnings: list[str] = []

    if not md_path.exists():
        return {"errors": [f"文件不存在: {md_path}"], "warnings": [], "summary": "文件缺失"}

    text = md_path.read_text(encoding="utf-8")
    images = IMAGE_PATTERN.findall(text)

    svg_count = 0
    missing = 0
    for img_path in images:
        # Skip web URLs
        if img_path.startswith(("http://", "https://", "//")):
            continue
        full_path = (base_dir / img_path).resolve()
        if not full_path.exists():
            errors.append(f"图片缺失: {img_path}")
            missing += 1
        elif full_path.suffix.lower() == ".svg":
            svg_count += 1
            warnings.append(f"SVG 图片需转换: {img_path}")

    return {
        "errors": errors,
        "warnings": warnings,
        "summary": f"检查: {len(images)} 个图片引用, {missing} 个缺失, {svg_count} 个 SVG",
    }


def validate_manuscript(
    md_path: Path,
    base_dir: Path | None = None,
    profile: str | None = None,
) -> dict:
    """Run all manuscript validations. Returns merged result."""
    if base_dir is None:
        base_dir = md_path.parent

    structure = validate_structure(md_path)
    formulas = validate_formulas(md_path, profile)
    attachments = validate_attachments(md_path, base_dir)

    all_errors = structure["errors"] + formulas["errors"] + attachments["errors"]
    all_warnings = structure["warnings"] + formulas["warnings"] + attachments["warnings"]

    return {
        "errors": all_errors,
        "warnings": all_warnings,
        "summary": {
            "structure": structure["summary"],
            "formulas": formulas["summary"],
            "attachments": attachments["summary"],
        },
        "has_errors": len(all_errors) > 0,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate manuscript")
    parser.add_argument("manuscript", help="Path to Markdown manuscript")
    parser.add_argument("--base-dir", help="Base directory for resolving image paths")
    parser.add_argument("--profile", help="Render profile for profile-specific checks")
    args = parser.parse_args()

    md = Path(args.manuscript)
    base = Path(args.base_dir) if args.base_dir else md.parent
    result = validate_manuscript(md, base, args.profile)

    print(f"# 源稿校验: {args.manuscript}")
    print()
    if result["errors"]:
        print(f"## Errors ({len(result['errors'])})")
        for e in result["errors"]:
            print(f"  - ❌ {e}")
    else:
        print("## Errors: ✅ 无")
    print()
    if result["warnings"]:
        print(f"## Warnings ({len(result['warnings'])})")
        for w in result["warnings"]:
            print(f"  - ⚠ {w}")
    else:
        print("## Warnings: ✅ 无")
    print()

    return 1 if result["has_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
