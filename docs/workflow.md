# 工作流总览

本文档描述论文项目的完整生命周期。

## 两种工作模式

| 模式 | 入口 | 适用场景 |
|------|------|----------|
| 编排模式 | `/paper-workflow init|run|qa|render` | 完整论文项目，按 17 阶段推进 |
| 单次任务 | 自然语言（如"搜知网储能论文"） | 单次操作，叶子 skill 直接响应 |

## 17 阶段模型（paper-workflow）

```
requirements → material_prep → literature_search → literature_dedup
  → deep_reading → evidence_matrix → research_design → data_analysis
  → charts_and_tables → outline → writing → citation_verification
  → polishing → formatting → originality_check → quality_qa → revision
```

完整说明见 `.claude/skills/paper-workflow/references/lifecycle.md`。

## 六阶段简版（单次任务模式）

适合不使用编排器的快速任务：

1. 文献调研 → nature-academic-search / cnki-search
2. 撰写初稿 → nature-writing
3. 制作图表 → nature-figure
4. 润色与数据 → nature-polishing / nature-data
5. 投稿回复 → nature-response
6. 汇报展示 → nature-paper2ppt

## 使用原则

- 先确认当前活跃论文（CONTEXT.md）
- 编排模式：用 `/paper-workflow` 命令管理
- 单次任务：直接描述需求，叶子 skill 自动响应
- paper-workflow 不会自动触发（`disable-model-invocation: true`）

## 常见误区

- 不要一次启动全部阶段
- 编排模式不要跳过 evidence_matrix 直接写作
- 不要把详细技能说明塞进根 README.md
