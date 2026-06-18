# Execution Contracts

每个阶段的 Execution Contract 定义了输入、输出、完成条件和 handoff 模板。所有 contract 文件位于 `contracts/<stage_id>.yaml`，必须通过 `schemas/stage-execution.schema.json` 校验。

## Contract Structure

| 字段 | 类型 | 必需 | 说明 |
|------|------|:--:|------|
| `stage_id` | string | ✅ | 17 阶段标识符 |
| `phase` | int (1-6) | ✅ | 用户视角 6 阶段编号 |
| `phase_label` | string | | 用户可见中文名 |
| `executor_type` | enum | ✅ | `script` / `skill_handoff` / `manual` / `hybrid` |
| `has_waiting_state` | bool | | skill_handoff 是否进入 waiting_for_user |
| `required_skill` | string\|null\|object | | skill_handoff 所需的 skill 名 |
| `script_module` | string\|null | | script/hybrid 阶段的 Python 模块 |
| `script_function` | string\|null | | script/hybrid 阶段的 Python 函数 |
| `followup_skill` | string\|null | | hybrid 阶段失败后的 handoff skill |
| `input_artifacts` | string[] | | 输入文件路径 |
| `output_artifacts` | string[] | ✅ | 期望输出文件路径 |
| `preconditions` | string[] | | 阶段启动前置条件 |
| `done_conditions` | string[] | ✅ | script/manual/hybrid 完成条件 |
| `handoff_done` | string[] | ✅* | skill_handoff handoff 生成条件 |
| `stage_done` | string[] | ✅* | skill_handoff 用户完成后条件 |
| `quality_checks` | string[] | | 完成后质量检查 |
| `user_confirmation_required` | bool | | 是否需要 confirm |
| `handoff_prompt_template` | string\|null | ✅* | skill_handoff prompt 模板 |
| `fallback_on_failure` | enum | | `block` / `skip` / `retry` / `manual` |
| `not_in_v0.2_mvp` | bool | | 是否排除在 v0.2 MVP 外 |

> ✅* = skill_handoff 阶段必需

## Condition Expression Syntax

```
file_exists:<relative_path>              # 文件存在且非空
record_count:<jsonl_path> > N            # JSONL 行数
record_count:<jsonl_path> >= N
csv_has_rows:<csv_path>                  # CSV 行数 > 1（含表头）
no_unresolved_cite_needed:<md_path>      # 无 [CITE NEEDED] 残留
qa_errors == 0                           # QA 报告中的 errors = 0
```

## Input Artifact Markers

- 普通路径：`literature/catalog.jsonl` — 必需存在
- `optional:` 前缀：`optional:materials/templates/reference.docx` — 不存在不 blocked

## required_skill Formats

```yaml
# 单一 skill（不分语言）
required_skill: nature-reader

# 按语言路由
required_skill:
  zh: cnki-search
  en: nature-academic-search

# 无可用的 skill
required_skill: null
```

## Done Conditions by Executor Type

| executor_type | 使用字段 | 检查时机 |
|---------------|----------|----------|
| `script` | `done_conditions` | 执行完成后 |
| `manual` | `done_conditions` | `confirm` 命令 |
| `hybrid` | `done_conditions` | 执行完成后（干净路径）|
| `skill_handoff` | `handoff_done` | `run` 命令（判断 handoff 是否生成）|
| `skill_handoff` | `stage_done` | `confirm` 命令（判断用户是否完成）|

> `confirm <stage>` 对 skill_handoff 阶段检查 `stage_done`，不是 `handoff_done`。
