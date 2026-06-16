# 6-Phase Paper Workflow

paper-workflow 的 17 个内部阶段映射为用户视角的 6 个语义阶段。每个阶段调用对应的 skill 或脚本。

## Phase Map

```
Phase 1: 文献检索下载
  └── literature_search  → skill_handoff (nature-academic-search / cnki-search)
  └── literature_dedup   → script (dedup.py)

Phase 2: 深度阅读
  └── deep_reading       → skill_handoff (nature-reader)
  └── evidence_matrix    → script (evidence_manager.py + user confirm)

Phase 3: 大纲
  └── outline            → skill_handoff (nature-writing 大纲模式)

Phase 4: 写论文
  └── writing            → skill_handoff (nature-writing 章节模式)
  └── citation_verification → hybrid (validate_citations.py + nature-citation)
  └── polishing          → skill_handoff (nature-polishing)

Phase 5: 图表
  └── charts_and_tables  → skill_handoff (nature-figure)

Phase 6: 输出/QA
  └── formatting         → script (render.py)
  └── quality_qa         → script (qa_report.py)
```

## 每阶段调用的 skill

| Phase | 阶段 | Skill |
|-------|------|-------|
| 1 | literature_search | nature-academic-search / cnki-search |
| 1 | literature_dedup | dedup.py (built-in script) |
| 2 | deep_reading | nature-reader |
| 2 | evidence_matrix | evidence_manager.py + user review |
| 3 | outline | nature-writing |
| 4 | writing | nature-writing |
| 4 | citation_verification | validate_citations.py + nature-citation |
| 4 | polishing | nature-polishing |
| 5 | charts_and_tables | nature-figure |
| 6 | formatting | render.py (built-in script) |
| 6 | quality_qa | qa_report.py (built-in script) |

## Handoff Prompt 中的 Materials 上下文

`outline`、`writing`、`polishing`、`charts_and_tables` 阶段的 handoff prompt 会自动列出 `materials/` 目录中的文件清单。这只列出文件名和类型，不全文塞入 prompt。

如果 `materials/` 目录不存在或为空，handoff prompt 中省略此部分，不影响执行。

## Manual 阶段（用户自驱动）

以下阶段在 v0.2 中为 manual——输出任务说明，由用户自行完成：

- `requirements` — 确认论文需求和研究问题
- `material_prep` — 准备参考材料到 materials/
- `research_design` — 设计实验方案
- `data_analysis` — 分析数据
- `originality_check` — 原创性自查

`revision` 阶段保留为 manual/future，v0.2 不实现。

## 用户确认点

以下阶段执行后需要用户运行 `confirm <stage>`：

| 阶段 | 确认内容 |
|------|----------|
| `literature_search` | 文献导入是否完成 |
| `deep_reading` | 阅读笔记是否覆盖关键方法 |
| `evidence_matrix` | citekey 是否匹配 |
| `outline` | 大纲结构是否满意 |
| `writing` | 章节内容是否正确 |
| `polishing` | 润色是否改变语义 |
| `charts_and_tables` | 图表是否准确 |
