#!/usr/bin/env python3
"""Validate a generated .tex file for basic structure."""

import re
import sys
from pathlib import Path


def validate_tex(tex_path: Path, project_dir: Path | None = None) -> dict:
    """Check a .tex file: existence, structure, image paths, citations.

    Returns:
        {
            "valid": bool,
            "errors": [str],
            "warnings": [str],
            "summary": str,
        }
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Existence
    if not tex_path.exists():
        return {
            "valid": False,
            "errors": [f"文件不存在: {tex_path}"],
            "warnings": [],
            "summary": "文件缺失",
        }

    text = tex_path.read_text(encoding="utf-8", errors="replace")

    # 2. Basic structure
    if r"\documentclass" not in text:
        warnings.append("未找到 \\documentclass — 可能不是完整 LaTeX 文档")
    if r"\begin{document}" not in text:
        errors.append("缺少 \\begin{document}")
    if r"\end{document}" not in text:
        errors.append("缺少 \\end{document}")
    if text.count(r"\begin{document}") != text.count(r"\end{document}"):
        errors.append("\\begin{document} 与 \\end{document} 数量不匹配")

    # 3. Image paths
    includegraphics = re.findall(r"\\includegraphics(?:\[.*?\])?\{(.*?)\}", text)
    base = project_dir or tex_path.parent
    for img_path in includegraphics:
        full = (base / img_path).resolve()
        if not full.exists():
            errors.append(f"图片路径不存在: {img_path}")

    # 4. Bibliographic references
    has_bib = bool(re.search(r"\\(?:bibliography|addbibresource)\{", text))
    has_cite = bool(re.search(r"\\(?:cite|citep|citeproc|autocite)\{", text))
    if not has_bib and not has_cite:
        warnings.append("未检测到参考文献引用命令")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "summary": (f"结构: {'完整' if not errors else '有问题'}, "
                    f"图片引用: {len(includegraphics)} 个, "
                    f"参考文献: {'有' if has_bib else '无'}"),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate a tex file")
    parser.add_argument("tex", help="Path to .tex file")
    parser.add_argument("--project", help="Project root for resolving image paths")
    args = parser.parse_args()

    project_dir = Path(args.project) if args.project else None
    result = validate_tex(Path(args.tex), project_dir)
    print(f"# tex 校验: {args.tex}")
    print(f"  valid: {result['valid']}")
    for e in result["errors"]:
        print(f"  ❌ {e}")
    for w in result["warnings"]:
        print(f"  ⚠ {w}")
    print(f"  {result['summary']}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
