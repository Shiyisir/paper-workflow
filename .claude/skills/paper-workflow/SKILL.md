---
name: paper-workflow
description: 论文写作编排器。管理论文项目的完整生命周期——从初始化、文献检索、证据矩阵构建到渲染输出和质量核验。通过 /paper-workflow 命令驱动，不替代学术判断。
disable-model-invocation: true
---

# paper-workflow

论文写作工作的唯一编排入口。不实现学术能力（搜索/阅读/润色/引用），只负责：收集需求 → 按阶段路由 → 调叶子 skill → 质量核验 → 推进。

## 触发条件

本 skill 仅响应显式命令前缀 `/paper-workflow`，**不会**被自然语言自动触发。

单次任务（如"搜知网储能论文""润色这段摘要"）由对应叶子 skill 的 `SKILL.md` 自行触发，不做中转。叶子 skill 分发关系见下文「单次任务 handoff 参考」。

## 核心命令

| 命令 | 功能 | 状态要求 |
|------|------|----------|
| `/paper-workflow init` | 在当前目录初始化论文项目 | 无已有项目 |
| `/paper-workflow status` | 展示当前阶段、产物、下一步 | state.yaml 存在 |
| `/paper-workflow resume` | 从断点恢复 | state.yaml 存在 |
| `/paper-workflow run <stage>` | 推进到指定阶段（含依赖检查） | 阶段 pending |
| `/paper-workflow run <stage> --override` | 跳过依赖强制执行 | — |
| `/paper-workflow qa` | 对当前阶段产物运行质量核验 | 当前阶段 done |
| `/paper-workflow render <profile>` | 用指定 profile 输出终稿 | manuscript/main.md 存在 |
| `/paper-workflow render <profile> --dry-run` | 预览渲染操作 | — |
| `/paper-workflow revise` | 进入投稿返修模式 | 终稿已输出 |

## 阶段标识符

`/paper-workflow run` 接受的阶段名（共 17 个）：

```
requirements, material_prep, literature_search, literature_dedup,
deep_reading, evidence_matrix, research_design, data_analysis,
charts_and_tables, outline, writing, citation_verification,
polishing, formatting, originality_check, quality_qa, revision
```

## 命令路由表（项目模式）

### init
```
→ 交互式提问（论文类型、学科、语言、检索偏好）
→ 根据 paper_type + research_type 计算跳过的阶段
→ scripts/init_project.py 生成项目骨架
→ 输出 state.yaml + config.yaml + artifact-manifest.jsonl
```

### status
```
→ scripts/workflow_state.py load_state()
→ 展示当前阶段、已完成阶段列表、下一可推进阶段
→ 产物清单（来自 artifact-manifest.jsonl）
--verbose → 展示所有阶段详情
```

### resume
```
→ scripts/workflow_state.py load_state()
→ 读取 current_stage → 检查该阶段状态
→ 如在 in_progress → 展示上下文，等待用户确认继续
→ 如在 blocked → 展示 blockers，提示修复路径
```

### run <stage>
```
→ scripts/workflow_state.py set_stage_status()
→ 依赖检查：depends_on 全部 done → 推进
→ 否则 → 标记 blocked，返回缺失条件
--override → 跳过依赖，写入 overrides 日志
→ 调用对应阶段执行器（初期为 stub，后续里程碑填充）
```

### qa
```
→ 读取当前阶段配置的 QA 检查项
→ 依次运行：validate_manuscript / validate_citations / validate_catalog / validate_docx_tex
→ 输出 QA 报告
```

### render <profile>
```
→ 加载 profile YAML（templates/profiles/<profile>.yaml）
→ scripts/render.py 执行渲染链
--dry-run → 预览操作列表，不生成文件
```

## 单次任务 handoff 参考

以下自然语言输入由对应叶子 skill 的 SKILL.md 自行触发，`paper-workflow` 不介入：

| 用户输入 | 应触发的叶子 skill |
|----------|-------------------|
| "搜知网…" / "CNKI 搜索…" | cnki-search |
| "search PubMed for…" / "搜索 Scopus…" | nature-academic-search |
| "润色这段…" / "polish this…" | nature-polishing |
| "读这篇论文" / "翻译这篇" | nature-reader |
| "核验引用" / "check citations" | nature-citation |
| "画这张图" / "做图表" | nature-figure |
| "模拟审稿" / "review this" | nature-reviewer |
| "回复审稿意见" | nature-response |
| "导出一篇论文引用" | cnki-export |
| "下载这篇论文" | cnki-download |

## 渲染 profile 速查

| Profile | 输出 | 适用场景 |
|---------|------|----------|
| `course-cn` | .docx | 中文课程论文 |
| `thesis-cn` | .docx | 中文学位论文 |
| `journal-word` | .docx | 英文期刊（Word 提交） |
| `journal-latex` | .tex | 英文期刊（LaTeX 提交） |
| `markdown-draft` | .md | 快速草稿，不含完整引用 |

## 文件结构

本 skill 的完整目录结构和各文件的职责详见 `references/lifecycle.md`。核心入口文件：
- `scripts/workflow_state.py` — 状态机引擎
- `scripts/init_project.py` — 项目初始化
- `scripts/render.py` — 渲染引擎
- `scripts/dedup.py` — 文献去重
- `scripts/validate_*.py` — 质量校验
- `schemas/*.schema.json` — JSON Schema 定义
- `templates/profiles/*.yaml` — 渲染配置
- `templates/csl/*.csl` — 引用格式
