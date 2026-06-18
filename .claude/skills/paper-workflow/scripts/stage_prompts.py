#!/usr/bin/env python3
"""Handoff prompt template engine for skill_handoff stages.

Renders structured task prompts from contract handoff_prompt_template
with live variables from config, state, catalog, and materials/.
"""
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPT_DIR))

from stage_executor import load_contract


# ---------------------------------------------------------------------------
# Fallback prompts per stage (used when contract template is missing/broken)
# ---------------------------------------------------------------------------

_FALLBACK_PROMPTS = {
    "literature_search": (
        "请使用 {skill} 为我搜索以下主题的学术文献。\n"
        "论文主题：{topic}\n"
        "学科领域：{discipline}\n"
        "语言偏好：{language}\n"
        "请将搜索结果整理后导入文献库 literature/catalog.jsonl。"
    ),
    "deep_reading": (
        "请使用 {skill} 精读以下论文的 PDF。\n"
        "论文列表：{catalog_summary}\n"
        "请生成完整的双语阅读笔记，输出到 literature/reading-notes/{{citekey}}.md。"
    ),
    "outline": (
        "请使用 {skill} 为以下论文撰写大纲。\n"
        "论文类型：{paper_type}  研究类型：{research_type}  学科：{discipline}\n"
        "请生成包含章节标题和每节核心论点的完整大纲。\n"
        "输出到 manuscript/outline.md。"
    ),
    "writing": (
        "请使用 {skill} 的章节模式，基于大纲 manuscript/outline.md 撰写论文。\n"
        "论文类型：{paper_type}\n"
        "请逐章撰写，用 [@citekey] 格式标注引用。\n"
        "输出到 manuscript/main.md。"
    ),
    "polishing": (
        "请使用 {skill} 润色论文 manuscript/main.md。\n"
        "语言要求：Nature-level academic English。"
    ),
    "charts_and_tables": (
        "请使用 {skill} 为论文制作图表。\n"
        "手稿：manuscript/main.md\n"
        "数据目录：analysis/\n"
        "请生成符合学术出版标准的图表，输出到 figures/ 和 tables/。"
    ),
}


# ---------------------------------------------------------------------------
# Template variables
# ---------------------------------------------------------------------------

def get_template_variables(
    stage_id: str,
    project_dir: Path,
    state: dict,
    config: dict,
) -> dict:
    """Build the variable dict for handoff prompt rendering.

    Returns a dict with at minimum:
        topic, discipline, language, paper_type, research_type,
        skill, stage_id, project_dir, materials_summary, catalog_summary,
        evidence_summary, claim_summary
    """
    contract = load_contract(stage_id)

    # Resolve required_skill
    skill = _resolve_skill(contract, config)

    # Core variables from config/state
    paper_type = config.get("paper_type", state.get("paper_type", "unknown"))
    research_type = config.get("research_type", state.get("research_type", "unknown"))
    discipline = config.get("discipline", state.get("discipline", "unknown"))
    language = config.get("language", state.get("language", "en"))
    topic = config.get("project_id", state.get("project_id", "unknown"))

    return {
        "topic": topic,
        "discipline": discipline,
        "language": language,
        "paper_type": paper_type,
        "research_type": research_type,
        "skill": skill,
        "stage_id": stage_id,
        "project_dir": str(project_dir),
        "materials_summary": _materials_summary(project_dir),
        "catalog_summary": _catalog_summary(project_dir),
        "evidence_summary": _file_summary(project_dir, "literature/evidence-matrix.csv", "evidence-matrix"),
        "claim_summary": _file_summary(project_dir, "citations/claim-citation-map.csv", "claim-citation-map"),
    }


def _resolve_skill(contract: dict, config: dict) -> str:
    """Resolve skill name from contract's required_skill (string or language map)."""
    required = contract.get("required_skill")

    if isinstance(required, str):
        return required
    if isinstance(required, dict) and required:
        lang = config.get("language", "en")
        # Try exact language match
        if lang in required:
            return required[lang]
        # Try zh fallback
        if lang == "en" and "zh" in required:
            pass  # fall through to first available
        if "zh" in required:
            return required["zh"]
        if "en" in required:
            return required["en"]
        # First available
        return list(required.values())[0]
    if required is None:
        return "none"

    return "unknown"


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------

def _materials_summary(project_dir: Path) -> str:
    """Generate a brief summary of materials/ directory contents."""
    materials_dir = project_dir / "materials"
    if not materials_dir.is_dir():
        return "暂无项目补充材料。"

    lines = ["可用项目材料："]
    found_any = False
    for sub in ["requirements", "templates", "examples", "notes"]:
        sub_dir = materials_dir / sub
        if sub_dir.is_dir():
            files = list(sub_dir.iterdir())
            for f in sorted(files):
                if f.is_file() and not f.name.startswith("."):
                    lines.append(f"- materials/{sub}/{f.name}")
                    found_any = True

    if not found_any:
        return "暂无项目补充材料。"
    return "\n".join(lines)


def _catalog_summary(project_dir: Path) -> str:
    """Generate a brief summary of catalog.jsonl contents."""
    cat_path = project_dir / "literature" / "catalog.jsonl"
    if not cat_path.exists():
        return "文献库为空。"
    try:
        import json
        count = 0
        titles = []
        with open(cat_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    count += 1
                    status = rec.get("screening_status", "?")
                    if status == "included" and len(titles) < 20:
                        titles.append(rec.get("title", "?")[:80])
                except json.JSONDecodeError:
                    pass
        summary = f"文献库共 {count} 条记录。"
        if titles:
            summary += "\n已收录文献：\n" + "\n".join(f"  - {t}" for t in titles)
        return summary
    except Exception:
        return "无法读取文献库。"


def _file_summary(project_dir: Path, rel_path: str, label: str) -> str:
    """Check if a file exists and return a one-line summary."""
    target = project_dir / rel_path
    if not target.exists():
        return f"{label}：尚不存在。"
    try:
        lines = target.read_text(encoding="utf-8", errors="ignore").strip().split("\n")
        return f"{label}：{len(lines)} 行。"
    except Exception:
        return f"{label}：存在但无法读取。"


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

def render_handoff_prompt(
    stage_id: str,
    project_dir: Path,
    state: dict,
    config: dict,
) -> str:
    """Render a handoff prompt from contract template + live variables.

    Falls back to built-in prompt if contract template is missing or rendering fails.
    """
    try:
        contract = load_contract(stage_id)
    except Exception:
        return _fallback(stage_id, {}, {})

    template = contract.get("handoff_prompt_template")
    if not template or not template.strip():
        return _fallback(stage_id, state, config)

    variables = get_template_variables(stage_id, project_dir, state, config)

    # Use str.format with safety — missing keys replaced with placeholder
    try:
        prompt = _safe_format(template, variables)
        return prompt.strip()
    except Exception:
        return _fallback(stage_id, state, config)


def _safe_format(template: str, variables: dict) -> str:
    """Format a template string, leaving missing keys as-is."""
    import string

    class SafeDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    formatter = string.Formatter()
    # Use the formatter with a safe dict wrapper
    result = []
    for literal_text, field_name, format_spec, conversion in formatter.parse(template):
        result.append(literal_text)
        if field_name is not None:
            try:
                obj = variables.get(field_name, "{" + field_name + "}")
                if format_spec:
                    obj = format(obj, format_spec)
                if conversion == "r":
                    obj = repr(obj)
                elif conversion == "s":
                    obj = str(obj)
                result.append(str(obj))
            except Exception:
                result.append("{" + field_name + "}")
    return "".join(result)


def _fallback(stage_id: str, state: dict, config: dict) -> str:
    """Return a built-in fallback prompt for the stage."""
    fb = _FALLBACK_PROMPTS.get(stage_id, "请执行阶段 '{stage_id}'。")
    variables = {
        "skill": "相关 skill",
        "topic": config.get("project_id", state.get("project_id", "unknown")),
        "discipline": config.get("discipline", state.get("discipline", "unknown")),
        "language": config.get("language", state.get("language", "en")),
        "paper_type": config.get("paper_type", state.get("paper_type", "unknown")),
        "research_type": config.get("research_type", state.get("research_type", "unknown")),
        "stage_id": stage_id,
        "catalog_summary": "文献库状态未知。",
    }
    try:
        return _safe_format(fb, variables).strip()
    except Exception:
        return f"请执行阶段 '{stage_id}'。"
