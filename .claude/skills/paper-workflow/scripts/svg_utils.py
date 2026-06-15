#!/usr/bin/env python3
"""SVG detection and conversion utilities for render pipeline."""

import re
import shutil
import subprocess
from pathlib import Path

SVG_REF_PATTERN = re.compile(r"!\[.*?\]\((.*?\.svg)\)", re.IGNORECASE)


def find_svg_references(manuscript_path: Path) -> list[Path]:
    """Find all SVG image references in a Markdown file.

    Returns list of resolved paths (relative to manuscript location).
    """
    if not manuscript_path.exists():
        return []
    text = manuscript_path.read_text(encoding="utf-8")
    base = manuscript_path.parent
    svg_paths = []
    seen = set()
    for m in SVG_REF_PATTERN.finditer(text):
        rel = m.group(1)
        if rel in seen:
            continue
        seen.add(rel)
        svg_paths.append(base / rel)
    return svg_paths


def _detect_converter() -> str | None:
    """Detect available SVG conversion tool. Returns 'rsvg' or 'cairosvg' or None."""
    if shutil.which("rsvg-convert"):
        return "rsvg"
    try:
        import cairosvg  # noqa: F401
        return "cairosvg"
    except ImportError:
        pass
    return None


def convert_svg_references(
    profile: dict,
    manuscript_path: Path,
    project_dir: Path,
) -> dict:
    """Check for SVG references, report tool availability, produce path map.

    Returns:
        {
            "svg_count": int,
            "converter": str | None,
            "convertible": bool,
            "warnings": [str],
            "path_map": {Path: Path},  # svg_path → target_path
        }
    """
    target_format = profile.get("convert_svg_to", "none")
    svg_refs = find_svg_references(manuscript_path)

    if not svg_refs:
        return {
            "svg_count": 0, "converter": None, "convertible": True,
            "warnings": [], "path_map": {},
        }

    converter = _detect_converter()
    warnings: list[str] = []
    path_map: dict[Path, Path] = {}

    if target_format == "none":
        warnings.append(f"Profile 未配置 SVG 转换 (convert_svg_to=none)，"
                        f"但发现 {len(svg_refs)} 个 SVG 引用")
        return {
            "svg_count": len(svg_refs), "converter": converter,
            "convertible": False, "warnings": warnings, "path_map": {},
        }

    if converter is None:
        warnings.append(
            f"未找到 SVG 转换工具。发现 {len(svg_refs)} 个 SVG 引用，"
            f"请安装 rsvg-convert 或 cairosvg。"
        )
        warnings.append(
            "安装方法: pip install cairosvg  或 安装 librsvg (rsvg-convert)"
        )
        return {
            "svg_count": len(svg_refs), "converter": None,
            "convertible": False, "warnings": warnings, "path_map": {},
        }

    # Build path map: existing SVG → target PNG/PDF
    for svg_path in svg_refs:
        if svg_path.exists():
            target_path = svg_path.with_suffix(f".{target_format}")
            path_map[svg_path] = target_path
        else:
            warnings.append(f"SVG 文件不存在: {svg_path}")

    return {
        "svg_count": len(svg_refs),
        "converter": converter,
        "convertible": converter is not None and len(path_map) > 0,
        "warnings": warnings,
        "path_map": path_map,
    }
