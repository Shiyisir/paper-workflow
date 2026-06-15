#!/usr/bin/env python3
"""Initialize a new paper project.

Creates config.yaml, state.yaml, artifact-manifest.jsonl,
and all runtime directories. Idempotent — will not overwrite
an existing project unless --force is given.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Map of paper_type → stage IDs to auto-skip
SKIP_MAP: dict[str, list[str]] = {
    "book_report": [
        "literature_search", "literature_dedup", "deep_reading",
        "evidence_matrix", "research_design", "data_analysis",
        "charts_and_tables",
    ],
    "literature_review": [
        "data_analysis", "charts_and_tables",
    ],
    "lab_report": [],
    "journal_article": [],
    "course_paper": [],
    "thesis": [],
    "proposal": [],
    "data_report": [],
    "survey_report": [],
    "project_proposal": [],
    "policy_report": [],
}

# 17 stages in dependency order
STAGE_IDS = [
    "requirements", "material_prep", "literature_search", "literature_dedup",
    "deep_reading", "evidence_matrix", "research_design", "data_analysis",
    "charts_and_tables", "outline", "writing", "citation_verification",
    "polishing", "formatting", "originality_check", "quality_qa", "revision",
]

# Dependency graph: stage_id → list of prerequisite stage_ids
DEPENDENCY_GRAPH: dict[str, list[str]] = {
    "material_prep": ["requirements"],
    "literature_search": ["requirements"],
    "literature_dedup": ["literature_search"],
    "deep_reading": ["literature_dedup"],
    "evidence_matrix": ["deep_reading", "literature_dedup"],
    "research_design": ["evidence_matrix"],
    "data_analysis": ["research_design"],
    "charts_and_tables": ["data_analysis"],
    "outline": ["requirements", "literature_dedup", "evidence_matrix", "research_design", "charts_and_tables"],
    "writing": ["outline", "evidence_matrix", "charts_and_tables"],
    "citation_verification": ["writing"],
    "polishing": ["citation_verification"],
    "formatting": ["polishing"],
    "originality_check": ["formatting"],
    "quality_qa": ["originality_check"],
    "revision": ["quality_qa"],
}

PAPER_TYPES = [
    "course_paper", "thesis", "proposal", "literature_review",
    "lab_report", "data_report", "survey_report", "journal_article",
    "book_report", "project_proposal", "policy_report",
]

RESEARCH_TYPES = [
    "theoretical", "review", "empirical", "experimental", "case", "survey",
]

DISCIPLINES = [
    "humanities", "social_science", "economics_management",
    "engineering", "medicine", "computer_science", "interdisciplinary",
]

LANGUAGES = ["zh", "en", "bilingual"]


def generate_project_id(slug: str) -> str:
    """Sanitize slug to a valid project_id."""
    return slug.strip().lower().replace(" ", "-")


def build_state(project_id: str, paper_type: str, research_type: str,
                discipline: str, language: str, target_journal: str | None,
                search_mode: str) -> dict:
    """Build a complete state.yaml dict."""
    now = datetime.now(timezone.utc).isoformat()

    stages = {}
    for sid in STAGE_IDS:
        skipped = sid in SKIP_MAP.get(paper_type, [])

        # Additional skip for theoretical type
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

    # requirements starts as in_progress
    stages["requirements"]["status"] = "in_progress"
    stages["requirements"]["started_at"] = now

    state = {
        "schema_version": 1,
        "project_id": project_id,
        "paper_type": paper_type,
        "research_type": research_type,
        "discipline": discipline,
        "language": language,
        "target_journal": target_journal,
        "current_stage": "requirements",
        "stages": stages,
        "overrides": [],
    }

    return state


def build_config(project_id: str, paper_type: str, research_type: str,
                 discipline: str, language: str, target_journal: str | None,
                 search_mode: str) -> dict:
    """Build a complete config.yaml dict."""
    return {
        "project_id": project_id,
        "paper_type": paper_type,
        "research_type": research_type,
        "discipline": discipline,
        "language": language,
        "target_journal": target_journal,
        "search_mode": search_mode,
        "citation_style": "gb-t-7714" if language == "zh" else "apa",
        "writing_language": language,
        "word_count_target": None,
        "auto_skip_stages": True,
        "qa_strict_mode": False,
        "search_capabilities": {
            "cnki_search": "available",
            "cnki_download": "available",
            "scopus": "unavailable",
            "crossref": "available",
            "pubmed": "available",
            "arxiv": "available",
            "sciencedirect": "unavailable",
        },
    }


def create_directories(project_dir: Path) -> list[Path]:
    """Create all runtime directories. Returns list of created dirs."""
    dirs = [
        "manuscript",
        "literature",
        "citations",
        "analysis/scripts",
        "analysis/tables",
        "analysis/figures",
        "analysis/logs",
        "figures",
        "tables",
        "outputs/latest",
        "outputs/qa",
        ".paper-workflow",
    ]
    created = []
    for d in dirs:
        full = project_dir / d
        full.mkdir(parents=True, exist_ok=True)
        created.append(full)
    return created


def project_exists(project_dir: Path) -> bool:
    """Check if a paper-workflow project already exists in this directory."""
    state_file = project_dir / ".paper-workflow" / "state.yaml"
    config_file = project_dir / ".paper-workflow" / "config.yaml"
    return state_file.exists() or config_file.exists()


def interactive_prompt() -> dict:
    """Interactively ask the user for project parameters."""
    print("=== paper-workflow init ===\n")

    # paper_type
    print("论文类型 (paper_type):")
    for i, pt in enumerate(PAPER_TYPES, 1):
        print(f"  {i}. {pt}")
    while True:
        choice = input(f"选择 [1-{len(PAPER_TYPES)}]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(PAPER_TYPES):
                paper_type = PAPER_TYPES[idx]
                break
        except ValueError:
            pass
        print(f"请输入 1-{len(PAPER_TYPES)} 之间的数字")

    # research_type
    print("\n研究类型 (research_type):")
    for i, rt in enumerate(RESEARCH_TYPES, 1):
        print(f"  {i}. {rt}")
    while True:
        choice = input(f"选择 [1-{len(RESEARCH_TYPES)}]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(RESEARCH_TYPES):
                research_type = RESEARCH_TYPES[idx]
                break
        except ValueError:
            pass
        print(f"请输入 1-{len(RESEARCH_TYPES)} 之间的数字")

    # discipline
    print("\n学科 (discipline):")
    for i, d in enumerate(DISCIPLINES, 1):
        print(f"  {i}. {d}")
    while True:
        choice = input(f"选择 [1-{len(DISCIPLINES)}]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(DISCIPLINES):
                discipline = DISCIPLINES[idx]
                break
        except ValueError:
            pass
        print(f"请输入 1-{len(DISCIPLINES)} 之间的数字")

    # language
    print("\n写作语言 (language):")
    print("  1. zh (中文)")
    print("  2. en (English)")
    print("  3. bilingual (中英双语)")
    while True:
        choice = input("选择 [1-3]: ").strip()
        if choice in ("1", "2", "3"):
            language = LANGUAGES[int(choice) - 1]
            break
        print("请输入 1-3")

    # target_journal
    target_journal = input("\n目标期刊 (可选，按回车跳过): ").strip()
    if not target_journal:
        target_journal = None

    # search_mode
    print("\n检索模式 (search_mode):")
    print("  1. quick (课程论文)")
    print("  2. standard (学位论文/普通投稿)")
    print("  3. systematic (系统综述 — 增强版)")
    while True:
        choice = input("选择 [1-2]: ").strip()
        if choice == "1":
            search_mode = "quick"
            break
        elif choice == "2":
            search_mode = "standard"
            break
        elif choice == "3":
            print("systematic 模式将在增强版中提供，当前使用 standard")
            search_mode = "standard"
            break
        print("请输入 1-2")

    # slug
    slug = input("\n项目简称 (英文缩写，如 my-thesis): ").strip()
    if not slug:
        slug = "paper-project"

    project_id = generate_project_id(slug)

    return {
        "project_id": project_id,
        "paper_type": paper_type,
        "research_type": research_type,
        "discipline": discipline,
        "language": language,
        "target_journal": target_journal,
        "search_mode": search_mode,
    }


def init_project(project_dir: Path, params: dict, force: bool = False) -> bool:
    """Initialize a paper project. Returns True on success."""
    project_dir = project_dir.resolve()

    # Check for existing project
    if project_exists(project_dir) and not force:
        print(f"错误：{project_dir} 中已存在 paper-workflow 项目。")
        print("使用 --force 强制重新初始化（会覆盖现有配置）。")
        return False

    # Build state and config
    state = build_state(**params)
    config = build_config(**params)

    # Create directories
    created = create_directories(project_dir)
    print(f"已创建 {len(created)} 个目录")

    # Write state.yaml
    state_path = project_dir / ".paper-workflow" / "state.yaml"
    with open(state_path, "w", encoding="utf-8") as f:
        yaml.dump(state, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  ✓ {state_path}")

    # Write config.yaml
    config_path = project_dir / ".paper-workflow" / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  ✓ {config_path}")

    # Write artifact-manifest.jsonl (empty)
    manifest_path = project_dir / ".paper-workflow" / "artifact-manifest.jsonl"
    manifest_path.write_text("", encoding="utf-8")
    print(f"  ✓ {manifest_path}")

    # Print summary
    skipped_stages = [
        sid for sid in STAGE_IDS
        if state["stages"][sid]["status"] == "skipped"
    ]
    print(f"\n项目初始化完成: {params['project_id']}")
    print(f"  论文类型: {params['paper_type']}")
    print(f"  研究类型: {params['research_type']}")
    print(f"  学科: {params['discipline']}")
    print(f"  语言: {params['language']}")
    if skipped_stages:
        print(f"  自动跳过阶段: {', '.join(skipped_stages)}")
    print(f"\n下一步: /paper-workflow status")

    return True


def main():
    parser = argparse.ArgumentParser(description="Initialize a paper-workflow project")
    parser.add_argument(
        "project_dir", nargs="?", default=".",
        help="Project root directory (default: current directory)"
    )
    parser.add_argument("--slug", help="Project short name (e.g., my-thesis)")
    parser.add_argument("--paper-type", choices=PAPER_TYPES, help="Paper type")
    parser.add_argument("--research-type", choices=RESEARCH_TYPES, help="Research type")
    parser.add_argument("--discipline", choices=DISCIPLINES, help="Discipline")
    parser.add_argument("--language", choices=LANGUAGES, help="Writing language")
    parser.add_argument("--target-journal", help="Target journal name")
    parser.add_argument("--search-mode", choices=["quick", "standard"], default="standard")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing project")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Skip interactive prompts (requires all CLI args)")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)

    if args.non_interactive or args.paper_type:
        # Non-interactive mode
        if not all([args.paper_type, args.research_type, args.discipline, args.language]):
            print("错误：非交互模式需要 --paper-type, --research-type, --discipline, --language")
            sys.exit(1)
        slug = args.slug or args.paper_type
        params = {
            "project_id": generate_project_id(slug),
            "paper_type": args.paper_type,
            "research_type": args.research_type,
            "discipline": args.discipline,
            "language": args.language,
            "target_journal": args.target_journal,
            "search_mode": args.search_mode,
        }
    else:
        params = interactive_prompt()

    success = init_project(project_dir, params, force=args.force)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
