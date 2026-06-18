# paper-workflow v0.2: Stage Executor Bridge

> 日期：2026-06-16 | 状态：草稿 | 基于 v0.1.2 实测

---

## 1. v0.1.2 当前能力与核心缺口

### 已实装（可工作）

| 能力 | 实现 | 测试 |
|------|:--:|:--:|
| 项目初始化 | `init_project.py` | 296 tests |
| 17 阶段状态机 | `workflow_state.py` + `commands.py` | ✅ |
| 文献库 CRUD | `literature_store.py` | ✅ |
| 5 级去重 | `dedup.py` | ✅ |
| 证据矩阵 | `evidence_manager.py` | ✅ |
| BibTeX/CSL 导出 | `export_references.py` | ✅ |
| 引文一致性校验 | `validate_citations.py` | ✅ |
| 文献库质量校验 | `validate_catalog.py` | ✅ |
| 源稿结构校验 | `validate_manuscript.py` | ✅ |
| 三轨渲染 | `render.py` | ✅ |
| docx 幂等后处理 | `postprocess_docx.py` | ✅ |
| 统一 QA 报告 | `qa_report.py` | ✅ |
| CLI --project 一致性 | v0.1.2 修复 | ✅ |
| 真实项目验证 | 2 个 smoke test 通过 | ✅ |

### 核心缺口

`commands.py` 的 `_execute_stage()` 函数：

```python
def _execute_stage(stage_id: str) -> dict:
    print(f"  [stub] 阶段 '{stage_id}' 的执行逻辑尚未实现")
    print(f"  [stub] 该阶段将在后续里程碑中填充")
    return {"executed": False, "reason": "stub — not yet implemented"}
```

17 个阶段全部走这个 stub。这意味着 `/paper-workflow run deep_reading` 或 `/paper-workflow run writing` 只改 `state.yaml` 中的状态，**不执行任何实际工作**。

**v0.2 的唯一目标：把这个 stub 换成真正的阶段分发器。**

---

## 2. 用户视角 6 阶段流程

v0.2 对用户暴露的不是 17 个阶段，而是 6 个语义清晰的论文写作阶段：

```
Phase 1: 文献检索下载     → literature_search + literature_dedup
Phase 2: 深度阅读         → deep_reading + evidence_matrix
Phase 3: 大纲             → outline
Phase 4: 写论文           → writing + citation_verification + polishing
Phase 5: 图表             → charts_and_tables
Phase 6: 输出/QA          → formatting + quality_qa
```

用户在 Claude Code 中输入 `/paper-workflow run <stage>` 或 `/paper-workflow resume` 时，系统自动推进到对应阶段，并调度执行器。

---

## 3. 17 阶段到 6 阶段的映射

```
Phase 1: 文献检索下载
  ├── requirements         → manual（用户陈述论文需求）
  ├── material_prep        → manual（用户准备材料）
  ├── literature_search    → skill_handoff（搜索 skill）
  └── literature_dedup     → script（dedup.py）

Phase 2: 深度阅读
  ├── deep_reading         → skill_handoff（nature-reader）
  └── evidence_matrix      → script + manual（evidence_manager.py + 用户审核）

Phase 3: 大纲
  └── outline              → skill_handoff（nature-writing 大纲模式）

Phase 4: 写论文
  ├── research_design      → manual（实验设计方案）
  ├── data_analysis        → manual（跑实验/分析数据）
  ├── writing              → skill_handoff（nature-writing 章节模式）
  ├── citation_verification → hybrid（validate_citations.py + nature-citation）
  └── polishing            → skill_handoff（nature-polishing）

Phase 5: 图表
  └── charts_and_tables    → skill_handoff（nature-figure）

Phase 6: 输出/QA
  ├── formatting           → script（render.py）
  ├── originality_check    → manual（用户自查）
  ├── quality_qa           → script（qa_report.py）
  └── revision             → manual / future（v0.3，不属于 v0.2 MVP 必跑流程）
```

---

## 4. Stage Execution Contract 数据结构

每个阶段的核心元数据定义为 Execution Contract。提案 schema：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Stage Execution Contract",
  "type": "object",
  "required": ["stage_id", "executor_type", "output_artifacts", "done_conditions"],
  "properties": {
    "stage_id": {
      "type": "string",
      "description": "17 阶段标识符"
    },
    "phase": {
      "type": "integer",
      "minimum": 1,
      "maximum": 6,
      "description": "对应用户视角 6 阶段"
    },
    "phase_label": {
      "type": "string",
      "description": "用户可见的阶段中文名"
    },
    "executor_type": {
      "type": "string",
      "enum": ["script", "skill_handoff", "manual", "hybrid"],
      "description": "执行器类型"
    },
    "has_waiting_state": {
      "type": "boolean",
      "default": false,
      "description": "skill_handoff 阶段是否进入 waiting_for_user 状态（handoff 已生成但用户尚未完成 skill 执行）"
    },
    "required_skill": {
      "type": ["string", "null"],
      "description": "skill_handoff 型必须指定，如 'nature-reader'"
    },
    "input_artifacts": {
      "type": "array",
      "items": { "type": "string" },
      "description": "阶段需要的输入文件路径（相对项目根）"
    },
    "output_artifacts": {
      "type": "array",
      "items": { "type": "string" },
      "description": "阶段产出的文件路径模板"
    },
    "preconditions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "阶段开始前必须满足的条件"
    },
    "done_conditions": {
      "type": "array",
      "items": { "type": "string" },
      "description": "阶段判定为 done 的条件列表"
    },
    "quality_checks": {
      "type": "array",
      "items": { "type": "string" },
      "description": "阶段完成后的质量检查项"
    },
    "user_confirmation_required": {
      "type": "boolean",
      "default": false
    },
    "handoff_prompt_template": {
      "type": ["string", "null"],
      "description": "skill_handoff 型阶段的任务描述模板"
    },
    "fallback_on_failure": {
      "type": "string",
      "enum": ["block", "skip", "retry", "manual"],
      "default": "block",
      "description": "执行失败时的处理策略"
    }
  }
}
```

### executor_type 语义

| 类型 | 执行方式 | 典型阶段 |
|------|----------|----------|
| `script` | `commands.py` 直接 import 并调用 Python 函数 | `literature_dedup`、`evidence_matrix`、`formatting`、`quality_qa` |
| `skill_handoff` | 生成结构化 handoff prompt，由 Claude Code 加载对应 skill 执行 | `deep_reading`、`outline`、`writing`、`polishing`、`charts_and_tables` |
| `manual` | 输出任务说明和完成标准，等待用户手动标记 done | `requirements`、`material_prep`、`research_design`、`data_analysis` |
| `hybrid` | 先走 script 自动检查，发现问题时生成 skill handoff | `citation_verification` |

---

## 5. 每个核心阶段的执行器设计

### 5.1 literature_search（skill_handoff + waiting_for_user）

```yaml
stage_id: literature_search
phase: 1
executor_type: skill_handoff
required_skill: nature-academic-search  # 或 cnki-search（按 config.language 路由）
input_artifacts:
  - .paper-workflow/config.yaml
output_artifacts:
  - literature/catalog.jsonl
  - .paper-workflow/search-log.jsonl
preconditions:
  - config.yaml 中有 search_mode 和 discipline

# 第一次 run：生成 handoff → 进入 waiting_for_user
handoff_done:
  - .paper-workflow/handoffs/literature_search.json 已生成
  - handoff prompt 已输出，包含 search skill、关键词、输出格式要求
  - stage 进入 waiting_for_user 状态

# 用户导入文献并确认后：再次检查 stage_done
stage_done:
  - catalog.jsonl 中存在 screening_status=included 的记录
  - search-log.jsonl 中存在至少一次检索日志
  - 用户已运行 confirm 确认导入完成

quality_checks:
  - 每篇 included 文献都有 DOI 或明确来源标识
user_confirmation_required: true
handoff_prompt_template: |
  请使用 {skill} 为我搜索以下主题的学术文献：
  论文主题：{topic}
  学科领域：{discipline}
  检索模式：{search_mode}
  语言偏好：{language}
  请将搜索结果（包括标题、作者、年份、期刊、DOI、摘要）整理后，
  我会筛选并导入文献库。
fallback_on_failure: manual
```

> **实现要点**：`literature_search` 的 `run` 第一次只生成 handoff，不应因为 catalog 还没有新增记录就直接 blocked。状态流转：`pending → in_progress → waiting_for_user`（handoff 已生成）→ 用户完成搜索和导入 → `confirm` → 检查 stage_done → `done`。

### 5.2 literature_dedup（script）

```yaml
stage_id: literature_dedup
phase: 1
executor_type: script
script_module: dedup
script_function: deduplicate_and_report
input_artifacts:
  - literature/catalog.jsonl
output_artifacts:
  - literature/catalog.jsonl（去重后更新）
  - literature/dedup-report.md
preconditions:
  - catalog.jsonl 存在且非空
done_conditions:
  - dedup-report.md 存在
  - dedup 后 catalog.jsonl 无重复 DOI
quality_checks:
  - 无 pending_review 项遗留
```

### 5.3 deep_reading（skill_handoff）

```yaml
stage_id: deep_reading
phase: 2
executor_type: skill_handoff
required_skill: nature-reader
input_artifacts:
  - literature/catalog.jsonl
  - literature/pdfs/
output_artifacts:
  - literature/reading-notes/{citekey}.md
preconditions:
  - catalog.jsonl 中存在 screening_status=included 的文献
done_conditions:
  - 每篇 included 文献都有对应的 reading-notes/{citekey}.md
  - 每篇阅读笔记包含关键方法、结果、可提取的证据
quality_checks:
  - 阅读笔记文件名与 catalog citekey 一致
  - 笔记内容非空
user_confirmation_required: true
handoff_prompt_template: |
  请使用 nature-reader 精读以下论文的 PDF：
  论文：{title}（{citekey}）
  PDF 路径：{pdf_path}
  重点关注：
  {focus_areas}
  请生成完整的双语阅读笔记，保留图表位置。
```

### 5.4 evidence_matrix（script + user confirmation）

```yaml
stage_id: evidence_matrix
phase: 2
executor_type: script
script_module: evidence_manager
input_artifacts:
  - literature/reading-notes/
  - literature/catalog.jsonl
output_artifacts:
  - literature/evidence-matrix.csv
  - citations/claim-citation-map.csv
preconditions:
  - 至少 1 篇 reading note 存在
done_conditions:
  - evidence-matrix.csv 中至少与 included 文献数相等的条目
  - claim-citation-map.csv 中至少 3 条 claim
quality_checks:
  - 每条 evidence 的 citekey 在 catalog.jsonl 中存在
user_confirmation_required: true
```

### 5.5 outline（skill_handoff）

```yaml
stage_id: outline
phase: 3
executor_type: skill_handoff
required_skill: nature-writing
input_artifacts:
  - .paper-workflow/config.yaml
  - literature/evidence-matrix.csv
  - citations/claim-citation-map.csv
output_artifacts:
  - manuscript/outline.md
preconditions:
  - evidence_matrix 阶段 done
done_conditions:
  - manuscript/outline.md 存在且含章节结构（至少 3 级标题）
quality_checks:
  - 每个核心章节至少对应 1 条 claim 或 evidence
user_confirmation_required: true
handoff_prompt_template: |
  请使用 nature-writing 的大纲模式，为以下论文撰写大纲：
  论文类型：{paper_type}
  研究类型：{research_type}
  学科：{discipline}
  已有证据：{evidence_summary}
  已有论点：{claim_summary}
  请生成包含章节标题和每节核心论点的完整大纲。
  输出到 manuscript/outline.md。
```

### 5.6 writing（skill_handoff）

```yaml
stage_id: writing
phase: 4
executor_type: skill_handoff
required_skill: nature-writing
input_artifacts:
  - manuscript/outline.md
  - literature/evidence-matrix.csv
  - citations/claim-citation-map.csv
  - literature/reading-notes/
output_artifacts:
  - manuscript/main.md
preconditions:
  - outline 阶段 done
  - evidence_matrix 阶段 done
done_conditions:
  - manuscript/main.md 存在
  - 所有 outline 中的章节均已填充内容
  - 文中 citekey 不包含 [CITE NEEDED]（除非用户主动保留）
quality_checks:
  - validate_manuscript.py 结构检查通过
  - 所有引用 citekey 在 catalog 中存在
user_confirmation_required: true
```

### 5.7 citation_verification（hybrid）

```yaml
stage_id: citation_verification
phase: 4
executor_type: hybrid
script_module: validate_citations
followup_skill: nature-citation
input_artifacts:
  - manuscript/main.md
  - literature/references.bib
  - literature/catalog.jsonl
output_artifacts:
  - outputs/qa/citation-report.md
preconditions:
  - writing 阶段 done
  - references.bib 存在
done_conditions:
  - citation-report.md 存在
  - 0 个孤立引用（正文有、bib 无）
  - 无残留 [CITE NEEDED]（或用户确认保留）
quality_checks:
  - citekey 在 bib 和 catalog 中一致
```

### 5.8 polishing（skill_handoff）

```yaml
stage_id: polishing
phase: 4
executor_type: skill_handoff
required_skill: nature-polishing
input_artifacts:
  - manuscript/main.md
output_artifacts:
  - manuscript/main.md（润色后更新）
preconditions:
  - writing 阶段 done
  - citation_verification 阶段 done
done_conditions:
  - manuscript/main.md 已被润色（可由用户确认）
quality_checks:
  - 无语法/拼写错误（由 skill 自身保证）
user_confirmation_required: true
```

### 5.9 charts_and_tables（skill_handoff）

```yaml
stage_id: charts_and_tables
phase: 5
executor_type: skill_handoff
required_skill: nature-figure
input_artifacts:
  - manuscript/main.md
  - analysis/（数据分析结果）
output_artifacts:
  - figures/*.svg
  - tables/*.csv
preconditions:
  - data_analysis 阶段 done（或用户已提供数据）
done_conditions:
  - figures/ 目录下有至少 1 个图表文件
  - 每个图表有对应的标题和说明
quality_checks:
  - 图表编号连续
  - 图表在 manuscript 中被引用
user_confirmation_required: true
```

### 5.10 formatting（script）

```yaml
stage_id: formatting
phase: 6
executor_type: script
script_module: render
script_function: render
input_artifacts:
  - manuscript/main.md
  - literature/references.bib
output_artifacts:
  - outputs/*-vNNN.*
  - outputs/latest/*
preconditions:
  - writing 阶段 done
done_conditions:
  - 至少一个 profile 渲染成功
  - outputs/latest/ 中有渲染产物
```

### 5.11 quality_qa（script）

```yaml
stage_id: quality_qa
phase: 6
executor_type: script
script_module: qa_report
script_function: run_all_checks_and_report
input_artifacts:
  - manuscript/main.md
  - literature/catalog.jsonl
  - literature/references.bib
  - outputs/
output_artifacts:
  - outputs/qa/qa-report-vNNN.md
preconditions:
  - formatting 阶段 done
done_conditions:
  - QA report 存在
  - errors 计数 = 0
quality_checks:
  - 所有 check 均已运行
```

---

## 6. script 型阶段如何自动执行

script 型阶段是最简单的——`commands.py` 直接 import 对应模块并调用：

```python
# stage_executor.py 伪代码
EXECUTORS = {
    "literature_dedup": {
        "type": "script",
        "module": "dedup",
        "function": "run_dedup",
        "args": lambda project_dir: {
            "catalog": project_dir / "literature" / "catalog.jsonl",
            "output": project_dir / "literature" / "catalog.jsonl",
            "report": project_dir / "literature" / "dedup-report.md",
        }
    },
    "formatting": {
        "type": "script",
        "module": "render",
        "function": "render",
        "args": lambda project_dir, config: {
            "profile": config.get("default_profile", "thesis-cn"),
            "input_md": project_dir / "manuscript" / "main.md",
            "output_dir": project_dir / "outputs",
            "project_dir": project_dir,
        }
    },
    "quality_qa": {
        "type": "script",
        "module": "qa_report",
        "function": "run_all_checks",
        "args": lambda project_dir: {"project_dir": project_dir}
    },
}

def execute_script_stage(stage_id, project_dir, config):
    spec = EXECUTORS[stage_id]
    mod = importlib.import_module(spec["module"])
    func = getattr(mod, spec["function"])
    kwargs = spec["args"](project_dir, config) if callable(spec["args"]) else spec["args"]
    return func(**kwargs)
```

---

## 7. skill_handoff 型阶段如何生成任务包

skill_handoff 型阶段不能用 Python 直接调用。执行流程：

```
1. 阶段进入 in_progress
2. stage_executor.py 读取 stage contract
3. 收集 input_artifacts 的状态（存在、行数、缺失）
4. 用 handoff_prompt_template 渲染出结构化任务提示
5. 将任务包写入 .paper-workflow/handoffs/<stage_id>.json（按阶段分文件，避免覆盖）
6. 更新 .paper-workflow/handoffs/latest.json 为最近一次 handoff 指针
7. 输出到 CLI："请执行以下 Skill 调用:",
   然后打印 handoff prompt
8. 等待用户/Claude 执行对应的 skill
9. 用户执行完成后，运行 done_conditions 检查
10. 满足 → 标记 done；不满足 → 保持 in_progress 并提示
```

### 7.1 handoff 文件格式

handoff 文件保存在 `.paper-workflow/handoffs/` 目录下，每个阶段一个文件：

```
.paper-workflow/handoffs/
├── literature_search.json
├── deep_reading.json
├── outline.json
├── writing.json
├── polishing.json
├── charts_and_tables.json
└── latest.json               ← 最近一次 handoff 指针（软链接或路径引用）
```

单个 handoff 文件内容：

```json
{
  "stage_id": "deep_reading",
  "generated_at": "2026-06-16T14:00:00Z",
  "status": "pending",
  "skill": "nature-reader",
  "task_prompt": "请使用 nature-reader 精读...",
  "input_files": {
    "literature/catalog.jsonl": {"exists": true, "records": 10},
    "literature/pdfs/": {"exists": false, "missing": ["kanani2023.pdf"]}
  },
  "expected_outputs": [
    "literature/reading-notes/kanani2023Enabled.md"
  ],
  "retry_count": 0
}
```

### 7.2 handoff prompt 渲染

模板使用 Python 的 `str.format()` 或 Jinja2：

```
请使用 {skill} 精读以下论文的 PDF：
论文：{title}（{citekey}）
...
```

变量从 `config.yaml`、`state.yaml`、`catalog.jsonl` 中实时读取。

---

## 8. manual 型阶段如何处理

manual 型阶段不自动执行任何操作，只输出任务说明：

```
阶段 'research_design' 需要你手动完成：

任务：设计实验方案
输入：literature/evidence-matrix.csv（已就绪）
输出：analysis/experiment-plan.md

完成标准：
- 明确列出要复现的实验和评估指标
- 明确列出改进方案的具体步骤

完成后运行 /paper-workflow run research_design --override 标记完成。
```

---

## 9. 阶段产物写入 artifact-manifest.jsonl

每个阶段完成时，`stage_executor.py` 将产物追加到 manifest：

```json
{
  "timestamp": "2026-06-16T14:30:00Z",
  "stage_id": "deep_reading",
  "action": "created",
  "artifacts": [
    "literature/reading-notes/kanani2023Enabled.md"
  ],
  "executor": "nature-reader",
  "duration_seconds": 180
}
```

---

## 10. 阶段完成条件判断

`_check_done_conditions()` 函数遍历 `done_conditions` 列表：

```python
def _check_done_conditions(stage_id: str, project_dir: Path) -> tuple[bool, list[str]]:
    contract = load_contract(stage_id)
    unmet = []
    for cond in contract["done_conditions"]:
        if not _evaluate_condition(cond, project_dir):
            unmet.append(cond)
    return len(unmet) == 0, unmet
```

条件评估支持简单表达式：
- `file_exists:<path>` → Path 存在且非空
- `record_count:<path> > N` → JSONL 行数 > N
- `csv_has_rows:<path>` → CSV 行数 > 1（有表头）
- `no_unresolved_cite_needed:<path>` → 无 `[CITE NEEDED]`
- `qa_errors == 0` → QA 报告 errors = 0

---

## 11. 阶段失败回写 blocked

```python
if not all_done and not override:
    # 标记为 blocked
    mark_stage_blocked(state, stage_id, f"产物不满足完成条件: {unmet}")
    save_state(state, project_dir)
    print(f"[BLOCKED] 阶段 '{stage_id}' 未完成:")
    for u in unmet:
        print(f"  - {u}")
```

`fallback_on_failure` 控制更细粒度的失败处理：
- `block` — 标记 blocked（默认）
- `skip` — 标记 skipped，记录原因
- `retry` — 最多重试 N 次
- `manual` — 降级为 manual 模式

---

## 12. 用户确认点设计

以下阶段要求用户确认后才能标记 done：

| 阶段 | 确认内容 | 确认方式 |
|------|----------|----------|
| `literature_search` | 导入哪些文献、排除哪些 | 交互式列表选择 |
| `deep_reading` | 阅读笔记是否覆盖了关键方法 | 确认提示 |
| `evidence_matrix` | 每条 evidence 的 citekey 是否正确 | 确认提示 |
| `outline` | 大纲结构是否符合预期 | 修改 outline.md 后确认 |
| `writing` | 章节内容质量 | 审阅后确认 |
| `polishing` | 润色是否改变了语义 | 对比确认 |
| `charts_and_tables` | 图表是否准确表达数据 | 确认提示 |

确认流程：

```
阶段 'deep_reading' 执行完成。

产物：
  literature/reading-notes/kanani2023Enabled.md（12KB）
  literature/reading-notes/barrera2022Rainfall.md（8KB）

请检查阅读笔记是否完整。确认后运行：
  /paper-workflow confirm deep_reading

或修改后运行：
  /paper-workflow confirm deep_reading
```

确认命令 `commands.py confirm <stage_id>` 的处理逻辑：

```python
def cmd_confirm(stage_id: str, override: bool = False, project: str | None = None) -> int:
    root = _resolve_project_dir(project)
    loaded = load_state(root)
    state, config = loaded["state"], loaded["config"]

    stage = get_stage(state, stage_id)
    if stage is None:
        print(f"[ERROR] 未知阶段: {stage_id}")
        return 1

    # 先运行 done_conditions
    all_met, unmet = _check_done_conditions(stage_id, root)

    if all_met or override:
        set_stage_status(state, stage_id, "done", override=override)
        save_state(state, root)
        print(f"[OK] 阶段 '{stage_id}' 已标记为 done。")
        return 0
    else:
        # 不满足 → 保持当前状态或标记 blocked
        print(f"[BLOCKED] 阶段 '{stage_id}' 不满足完成条件：")
        for u in unmet:
            print(f"  - {u}")
        if stage.get("status") != "blocked":
            mark_stage_blocked(state, stage_id, f"confirm 检查失败: {unmet}")
            save_state(state, root)
        print("修复后重新运行 confirm，或使用 --override 强制确认。")
        return 1
```

命令签名：

```bash
python scripts/commands.py confirm deep_reading --project /path/to/project
python scripts/commands.py confirm deep_reading --project /path/to/project --override
```

---

## 13. commands.py 中 `_execute_stage()` 改造

现有 stub：

```python
def _execute_stage(stage_id: str) -> dict:
    print(f"  [stub] 阶段 '{stage_id}' 的执行逻辑尚未实现")
    return {"executed": False, "reason": "stub"}
```

v0.2 替换为：

```python
def _execute_stage(stage_id: str, project_dir: Path, state: dict, config: dict) -> dict:
    """Execute a stage using its registered executor."""
    contract = load_contract(stage_id)
    if contract is None:
        # 未知阶段或未注册的阶段 → fallback 到 manual
        return _execute_manual_stage(stage_id, project_dir)

    executor_type = contract["executor_type"]

    if executor_type == "script":
        return _execute_script_stage(stage_id, project_dir, config)
    elif executor_type == "skill_handoff":
        return _execute_skill_handoff_stage(stage_id, project_dir, state, config)
    elif executor_type == "hybrid":
        return _execute_hybrid_stage(stage_id, project_dir, state, config)
    elif executor_type == "manual":
        return _execute_manual_stage(stage_id, project_dir)
    else:
        return {"executed": False, "reason": f"未知 executor_type: {executor_type}"}
```

新增文件 `stage_executor.py` 包含：
- `load_contract(stage_id)` — 从 contract registry 加载阶段定义
- `_execute_script_stage()` — 脚本执行
- `_execute_skill_handoff_stage()` — handoff 生成
- `_execute_hybrid_stage()` — 混合执行
- `_execute_manual_stage()` — 手动提示
- `_check_done_conditions()` — 完成条件检查
- `_log_artifact()` — 产物写入 manifest

新增文件 `stage_prompts.py` 包含：
- `render_handoff_prompt()` — 从模板 + 变量渲染 handoff prompt
- 每个 skill_handoff 阶段的 prompt 模板

---

## 14. v0.2 MVP 范围

### P0（必须实现）

| 功能 | 说明 |
|------|------|
| `stage_executor.py` | 核心执行器分发框架 |
| `stage_prompts.py` | handoff prompt 引擎 |
| contract registry | 17 个阶段的 execution contract 定义（YAML/JSON） |
| 4 个 script 型阶段可用 | `literature_dedup`、`evidence_matrix`、`formatting`、`quality_qa` |
| 1 个 hybrid 型阶段可用 | `citation_verification` |
| 6 个 skill_handoff 型阶段生成 handoff | `literature_search`、`deep_reading`、`outline`、`writing`、`polishing`、`charts_and_tables` |
| 6 个 manual 型阶段可用 | `requirements`、`material_prep`、`research_design`、`data_analysis`、`originality_check`、`revision` |
| `commands.py confirm <stage>` | 用户确认命令 |
| `commands.py` 中 `_execute_stage()` 替换 | 路由到 stage_executor |
| artifact 自动写入 manifest | 阶段完成时自动追加 |
| done_conditions 自动检查 | 产物存在性 + 质量检查 |

### P1（应该实现）

| 功能 | 说明 |
|------|------|
| handoff prompt 模板变量渲染 | 从 config/state/catalog 实时取值 |
| stage-handoff.json 持久化 | 支持中断恢复 |
| 用户确认交互 | 关键阶段确认后标记 done |
| 参考文档 | `references/stage-executors.md`、`references/execution-contracts.md`、`references/phase6-workflow.md` |

### P2（可选的 polish）

| 功能 | 说明 |
|------|------|
| `stage-execution.schema.json` | execution contract 的 JSON Schema |
| 阶段耗时统计 | 记录在 artifact-manifest 中 |
| retry 逻辑 | `fallback_on_failure = retry` 时的重试 |

---

## 15. v0.2 不做什么

明确排除以下功能（推迟到 v0.3 或 future）：

- `revision-log.jsonl` 和 `/paper-workflow revise`
- 系统综述完整纳排流程（screening.csv / PRISMA）
- 多 Subagent 并行阅读
- Hook 二次校验
- 批量 PDF 自动下载
- 完整数据分析适配器
- 更多学校/期刊 Word 模板
- 全自动"一句话写论文"模式
- LaTeX PDF 编译

---

## 16. 测试策略

### 单元测试

| 测试对象 | 覆盖内容 |
|----------|----------|
| `stage_executor.load_contract()` | 所有阶段 ID 都有对应 contract |
| `stage_executor._check_done_conditions()` | 各种 condition 评估逻辑 |
| `stage_prompts.render_handoff_prompt()` | 模板变量替换正确 |
| `_execute_script_stage()` | 每个 script 型阶段都能正确调用 |
| `_execute_skill_handoff_stage()` | 生成正确的 handoff JSON 和 prompt |

### 集成测试

| 测试场景 | 验证点 |
|----------|--------|
| 完整 Phase 1（文献搜索+去重） | catalog 有记录 → dedup 执行 → report 生成 |
| 完整 Phase 6（渲染+QA） | manuscript 存在 → render 成功 → QA 可运行 |
| 中断恢复 | skill_handoff 阶段生成 handoff.json → 重启后可从 handoff 恢复 |
| 从任意目录运行 | `--project` 参数 + 所有阶段执行器正确解析路径 |

### 端到端测试

使用 `tests/fixtures/mini-paper/`（已有 fixture），完整跑通 6 阶段：

```
init → literature_dedup → evidence_matrix → formatting → quality_qa
```

（skill_handoff 阶段在 fixture 测试中 mock 为 manual 模式，验证 handoff 文件生成即可）

---

## 17. 风险清单

| 风险 | 概率 | 影响 | 缓解 |
|------|:---:|:---:|------|
| 阶段间数据依赖断裂 | 中 | 高 | preconditions 检查 + blocked 状态 |
| handoff prompt 变量渲染失败 | 中 | 中 | 模板渲染失败时 fallback 到 manual |
| 用户跳过确认导致坏数据 | 中 | 中 | key stages 保留 `user_confirmation_required: true` |
| contract 定义与实际 skill 能力不匹配 | 中 | 中 | 每个 contract 在 smoke test 中验证 |
| 旧版 state.yaml 缺少新字段 | 低 | 低 | schema_version 升级 + 迁移 |

---

## 18. 后续 implementation plan 建议

```
M1: Contract Registry + stage_executor.py 框架
  → 所有 17 阶段 contract 定义（YAML）
  → _execute_stage() 路由到新执行器
  → 4 个 script 型阶段 + 1 个 hybrid 型阶段可工作

M2: skill_handoff 引擎
  → stage_prompts.py 模板渲染
  → stage-handoff.json 生成
  → 6 个 skill_handoff 型阶段可用

M3: manual 阶段 + 用户确认
  → commands.py confirm 命令
  → 用户确认交互流程
  → 5 个 manual 型阶段任务说明

M4: 参考文档 + 集成测试 + 端到端测试

M5: smoke test（真实论文项目完整 6 阶段）
```

每个里程碑独立可验证、独立可提交。

---

## 附录 A：contract registry 示例

```yaml
# .claude/skills/paper-workflow/contracts/literature_search.yaml
stage_id: literature_search
phase: 1
phase_label: 文献检索
executor_type: skill_handoff
required_skill:
  en: nature-academic-search
  zh: cnki-search
input_artifacts:
  - .paper-workflow/config.yaml
output_artifacts:
  - literature/catalog.jsonl
preconditions:
  - "config.yaml has discipline and search_mode"
done_conditions:
  - "file_exists:literature/catalog.jsonl"
  - "record_count:literature/catalog.jsonl > 0"
quality_checks:
  - "every included record has DOI or source note"
user_confirmation_required: true
fallback_on_failure: manual
```

## 附录 B：_execute_stage 改造前后对比

**Before（v0.1.2）**：
```python
def _execute_stage(stage_id: str) -> dict:
    print(f"  [stub] 阶段 '{stage_id}' 的执行逻辑尚未实现")
    return {"executed": False, "reason": "stub"}
```

**After（v0.2）**：
```python
def _execute_stage(stage_id: str, project_dir: Path,
                   state: dict, config: dict) -> dict:
    contract = load_contract(stage_id)
    if contract is None:
        return _fallback_manual(stage_id)
    executor_map = {
        "script": _execute_script_stage,
        "skill_handoff": _execute_skill_handoff_stage,
        "hybrid": _execute_hybrid_stage,
        "manual": _execute_manual_stage,
    }
    return executor_map[contract["executor_type"]](
        stage_id, contract, project_dir, state, config
    )
```
