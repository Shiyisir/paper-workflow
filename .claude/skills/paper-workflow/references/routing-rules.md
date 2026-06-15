# 状态机、跳转与回退规则

## 状态取值

| 状态 | 含义 |
|------|------|
| `pending` | 尚未开始，等待前置依赖完成 |
| `in_progress` | 当前正在执行 |
| `done` | 已完成，QA 状态另行记录 |
| `skipped` | 根据论文类型自动跳过 |
| `blocked` | 依赖未满足或有 blocker，无法推进 |

## 依赖图

```
requirements ───────────────────────────────────────────────┐
    │                                                        │
    ├── material_prep ───────────────────────────────────┐   │
    │                                                     │   │
    ├── literature_search ──→ literature_dedup            │   │
    │         │                    │                      │   │
    │         │                    ├── deep_reading       │   │
    │         │                    │       │              │   │
    │         │                    │       └── evidence_matrix
    │         │                    │               │
    │         │                    │               ├── research_design
    │         │                    │               │       │
    │         │                    │               │       ├── data_analysis
    │         │                    │               │       │       │
    │         │                    │               │       │       ├── charts_and_tables
    │         │                    │               │       │       │       │
    └─────────┼────────────────────┼───────────────┼───────┼───────┼─── outline
              │                    │               │       │       │       │
              │                    │               └───────┼───────┼─── writing
              │                    │                       │       │       │
              │                    │                       │       │       ├── citation_verification
              │                    │                       │       │       │       │
              │                    │                       │       │       │       ├── polishing
              │                    │                       │       │       │       │       │
              │                    │                       │       │       │       │       ├── formatting
              │                    │                       │       │       │       │       │       │
              │                    │                       │       │       │       │       │       ├── originality_check
              │                    │                       │       │       │       │       │       │       │
              │                    │                       │       │       │       │       │       │       └── quality_qa
              │                    │                       │       │       │       │       │       │
              └────────────────────┴───────────────────────┴───────┴───────┴───────┴───────┴─── revision
```

## 推进规则

### 正常推进：`run <stage>`

1. 检查 stage 的 `depends_on` 列表
2. 所有 depends_on 中的阶段 status 必须为 `done` 或 `skipped`
3. 满足 → 设置 stage.status = `in_progress` → 执行阶段逻辑 → 完成时设为 `done`
4. 不满足 → 设置 stage.status = `blocked`，记录缺失条件到 `blockers`

### 强制推进：`run <stage> --override`

1. 跳过依赖检查
2. 直接设置 stage.status = `in_progress`
3. 在 state.yaml 的 `overrides` 字段追加记录：
   ```yaml
   overrides:
     - stage: <stage_id>
       timestamp: <ISO8601>
       reason: "manual override"
       missing_deps: [<unmet_stage_ids>]
   ```

## 回退规则

### writing 讨论章证据不足
```
writing (in_progress)
→ 定向补检 → literature_search (重新 in_progress)
→ 搜索完成 → literature_dedup → evidence_matrix
→ 更新证据矩阵 → 回到 writing
```

### revision 审稿返修
```
revision (in_progress)
→ 回复审稿意见 → 修改源稿
→ 从 polishing 重新走 → formatting → originality_check → quality_qa
```

### QA 未通过
```
任何阶段 QA 未通过 → 该阶段回到 in_progress 状态
→ 修复问题 → 重新 QA
```

## 阶段跳过逻辑

在 `init` 时，根据 `paper_type` 自动标记跳过：

| 论文类型 | 自动跳过 |
|----------|----------|
| book_report | literature_search, literature_dedup, deep_reading, evidence_matrix, research_design, data_analysis, charts_and_tables |
| literature_review | data_analysis, charts_and_tables |
| lab_report | literature_search（可选）, deep_reading（可选） |
| theoretical journal_article | data_analysis（如有数据则保留） |

## 阻塞处理

`/paper-workflow status` 检测到 blocked 阶段时：
1. 展示 blocker 原因
2. 给出修复路径（例如"请先完成 literature_search"）
3. 用户可选择 `--override` 跳过或先满足依赖
