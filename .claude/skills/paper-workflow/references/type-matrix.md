# 论文类型 × 阶段矩阵

## 阶段需求矩阵

| 阶段 | course_paper | thesis | journal_article | literature_review | lab_report | book_report | proposal |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| requirements | ● | ● | ● | ● | ● | ● | ● |
| material_prep | ○ | ● | ○ | ○ | ● | ○ | ○ |
| literature_search | ● | ● | ● | ● | ○ | - | ○ |
| literature_dedup | ● | ● | ● | ● | ○ | - | ○ |
| deep_reading | ○ | ● | ○ | ○ | ○ | - | ○ |
| evidence_matrix | ○ | ● | ● | ● | ○ | - | ○ |
| research_design | ○ | ● | ● | ○ | ● | - | ● |
| data_analysis | ○ | ○ | ○ | - | ● | - | ○ |
| charts_and_tables | ○ | ○ | ○ | - | ● | - | ○ |
| outline | ● | ● | ● | ● | ● | ● | ● |
| writing | ● | ● | ● | ● | ● | ● | ● |
| citation_verification | ○ | ● | ● | ● | ○ | ○ | ○ |
| polishing | ○ | ● | ● | ○ | ○ | ○ | ○ |
| formatting | ○ | ● | ● | ○ | ○ | ○ | ○ |
| originality_check | ○ | ● | ● | ○ | ○ | ○ | ○ |
| quality_qa | ● | ● | ● | ● | ● | ● | ● |
| revision | - | - | ○ | - | - | - | - |

- ● 必需 | ○ 可选/按需 | - 自动跳过

## research_type 影响

| research_type | 特点 |
|---------------|------|
| theoretical | data_analysis 和 charts_and_tables 通常跳过（纯理论推导） |
| review | literature_search 必需，但 data_analysis 和 charts_and_tables 跳过 |
| empirical | 完整流程，data_analysis 必需 |
| experimental | 完整流程，lab_report 路径 |
| case | 完整流程，evidence_matrix 和 data_analysis 合并进行 |
| survey | 类似 empirical，charts_and_tables 侧重统计展示 |

## 跳过逻辑实现

`init_project.py` 根据 `paper_type` 在 state.yaml 中设置对应阶段 status = `skipped`：

```python
SKIP_MAP = {
    "book_report": [
        "literature_search", "literature_dedup", "deep_reading",
        "evidence_matrix", "research_design", "data_analysis",
        "charts_and_tables",
    ],
    "literature_review": ["data_analysis", "charts_and_tables"],
    "lab_report": [],  # 可选，由用户决定
    "journal_article": [],  # theoretical 类型自动跳过 data_analysis
}
```
