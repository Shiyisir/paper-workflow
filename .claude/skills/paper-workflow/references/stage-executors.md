# Stage Executors

paper-workflow 的阶段通过 Execution Contract 定义如何执行。每个阶段属于以下四种执行器类型之一。

## Executor Types

| 类型 | 执行方式 | 状态流转 |
|------|----------|----------|
| `script` | Python import + 函数调用 | pending → in_progress → done/blocked |
| `skill_handoff` | 生成 handoff prompt，用户/skill 执行 | pending → in_progress → waiting_for_user → done |
| `manual` | 输出任务说明，用户手动完成 | pending → in_progress → pending_confirmation → done |
| `hybrid` | 先 script 检查，有问题生成 handoff | pending → in_progress → done 或 waiting_for_user |

## Script Stages

Script 阶段直接调用已有 Python 脚本。执行器 import 对应模块并调用函数，完成后自动检查 done_conditions。

如果 `user_confirmation_required: true`，执行后进入 `pending_confirmation` 状态，等待用户 `confirm`。

**v0.2 script 阶段**：`literature_dedup`、`evidence_matrix`、`formatting`、`quality_qa`

## Skill Handoff Stages

Skill handoff 阶段不能直接被 Python 调用。执行流程：

1. `run <stage>` 读取 contract 和 input_artifacts
2. 渲染 handoff_prompt_template，注入变量（topic/discipline/config/catalog）
3. 写入 `.paper-workflow/handoffs/<stage_id>.json`
4. 输出 prompt 到 CLI
5. 状态进入 `waiting_for_user`
6. 用户完成 skill 执行后，运行 `confirm <stage>`，检查 stage_done
7. 通过 → done

**v0.2 skill_handoff 阶段**：`literature_search`、`deep_reading`、`outline`、`writing`、`polishing`、`charts_and_tables`

## Manual Stages

Manual 阶段输出结构化任务说明，用户自行完成后运行 `confirm`。

**v0.2 manual 阶段**：`requirements`、`material_prep`、`research_design`、`data_analysis`、`originality_check`、`revision`

## Hybrid Stage

Hybrid 阶段先走 script 路径自动检查。如果检查通过 → 直接 done；如果发现问题 → 生成 skill handoff。

**v0.2 hybrid 阶段**：`citation_verification`

## Status Values

v0.2 完整状态集合：

| 状态 | 含义 |
|------|------|
| `pending` | 尚未开始 |
| `in_progress` | 正在执行 |
| `waiting_for_user` | handoff 已生成，等待用户执行 skill |
| `pending_confirmation` | 产物已生成，等待用户 confirm |
| `done` | 完成 |
| `skipped` | 已跳过 |
| `blocked` | 前置条件未满足或 done_conditions 检查失败 |

## Materials Directory

每篇论文项目包含 `materials/` 目录，存放用户提供的参考材料：

- `materials/requirements/` — 论文要求、投稿指南、格式规范
- `materials/templates/` — Word/LaTeX 模板、reference.docx
- `materials/examples/` — 范文、参考样稿
- `materials/notes/` — 用户想法、导师要求

`materials/` 不是正式文献库，不参与 citation validation，不作为硬依赖。
