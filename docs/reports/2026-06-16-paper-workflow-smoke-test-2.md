# paper-workflow Smoke Test 2 报告

> 日期：2026-06-16 | 版本：v0.1.1 | 状态：通过

## 测试项目

| 项目 | 值 |
|------|-----|
| 路径 | `F:\Documents\Projects\Paper-Workflow\机器学习课程大作业\papers\03-rainfall-prediction` |
| 论文 | 基于LSTM集成方法的降雨预测复现与改进 |
| 类型 | 课程论文（course_paper） |
| 研究类型 | 实验报告（experimental） |
| 学科 | 计算机科学（computer_science） |
| 语言 | 中文 |

## 测试数据规模

| 数据项 | 数量 |
|--------|:--:|
| 文献记录（catalog.jsonl） | 5 |
| 证据条目（evidence-matrix.csv） | 5 |
| 论点（claim-citation-map.csv） | 5（C001–C005） |
| 正文引用 citekey | 5 个 |
| 真实 PDF | 1 篇（1.5 MB） |
| 数据集 | Rain in Australia（145,460 条，CSV） |

## 执行步骤与结果

| 步骤 | 命令 | 结果 |
|------|------|:--:|
| init | `init_project.py --slug ml-rainfall-prediction ...` | ✅ |
| catalog 写入 | `literature_store.append_records()` | ✅ 5 条 |
| dedup | `dedup.py --catalog ...` | ✅ 0 duplicates |
| refs 导出 | `export_references.py --format both` | ✅ bib 5 + csl 5 |
| evidence | `evidence_manager.add_evidence_entry()` | ✅ 5 条 |
| claims | `evidence_manager.add_claim()` | ✅ 5 条，C001–C005 |
| 17 阶段 | `commands.py run <stage>` | ✅ 全部跑通 |
| render md | `render.py --profile markdown-draft` | ✅ draft-v001.md (5.2 KB) |
| render docx | `render.py --profile thesis-cn` | ✅ thesis-cn-v001.docx (14.7 KB) |
| render tex | `render.py --profile journal-latex` | ✅ manuscript-v001.tex (8.3 KB) |
| QA | `qa_report.py --project .` | ⚠ passed_with_warnings |

## 输出文件

```
outputs/
├── draft-v001.md              # markdown-draft (5.2 KB)
├── thesis-cn-v001.docx        # thesis-cn (14.7 KB)
├── manuscript-v001.tex        # journal-latex (8.3 KB)
├── latest/
│   ├── draft.md
│   ├── thesis-cn.docx
│   └── manuscript.tex
└── qa/
    └── qa-report-v001.md
```

## QA 结果

- **总体状态**: `passed_with_warnings`
- **Errors**: 0
- **Warnings**: 1（evidence gap: 5 citekeys 未在 claim-citation-map 中交叉引用，符合设计预期）
- **Checks**: 5（catalog / citations / manuscript / docx / tex）

## 与第一次 Smoke Test 对比

| 维度 | 测试1（石漠化综述） | 测试2（降雨预测） |
|------|:--:|:--:|
| 论文类型 | course_paper / review | course_paper / experimental |
| 学科 | interdisciplinary | computer_science |
| 文献数 | 5 | 5 |
| 真实 PDF | 无 | 有（1.5 MB） |
| 真实数据集 | 无 | 有（14.5 万条 CSV） |
| 手稿规模 | ~800 字 | ~1500 字（19 标题 + 表格） |
| docx 大小 | 12.2 KB | 14.7 KB |
| tex 大小 | 3.7 KB | 8.3 KB |
| QA 结果 | passed_with_warnings | passed_with_warnings |

两次 Smoke Test 覆盖了差异明显的两个场景：综述型（review/interdisciplinary）和实验报告型（experimental/computer_science），v0.1.1 均稳定跑通。

## 新发现的边界情况

1. **API 参数名不一致**：`literature_store.py` 和 `search_logger.py` 使用 `project_root`，但 `evidence_manager.py`、`export_references.py`、`render.py`、`qa_report.py` 使用 `project_dir`。跨模块调用时容易误传关键字参数。

2. **`commands.py` 不支持 `--project`**：`status`、`resume`、`run` 子命令要求用户 `cd` 到项目目录，但 `render.py` 和 `qa_report.py` 支持 `--project`，使用方式不一致。

3. **`export_references.py` 缺少 `--project` 提示**：虽然有 `--project` 参数，但未设置 `default`，未传时直接报 AttributeError 而非友好提示。

## 结论

v0.1.1 已通过两个真实论文项目验证，具备稳定 MVP 使用价值。建议先做 v0.1.2 polish patch 修复上述 API/CLI 一致性问题，再进入 v0.2 规划。
