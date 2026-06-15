# 17 阶段生命周期详细说明

> 每个阶段的输入、输出、执行器映射和质量检查项。

## 阶段 1：requirements（需求确认）

- **类型**：必需
- **输入**：用户意图
- **输出**：config.yaml 中的 paper_type, research_type, discipline, language, target_journal
- **执行方式**：`/paper-workflow init` 交互式提问
- **QA**：确认论文类型-阶段跳过逻辑正确

## 阶段 2：material_prep（材料准备）

- **类型**：按需
- **输入**：导师要求、数据来源、已有材料清单
- **输出**：material_prep 阶段记录在 state.yaml 中
- **执行方式**：AI 对话引导，收集材料清单
- **QA**：材料清单完整，不存在"缺少关键数据"的阻塞

## 阶段 3：literature_search（文献检索）

- **类型**：按需（读书报告自动跳过）
- **输入**：研究主题、关键词、学科路由表
- **输出**：search-log.jsonl（检索记录）、catalog.jsonl（文献元数据）
- **执行方式**：`nature-academic-search`（英文）或 `cnki-search`（中文），按 search-profiles.md 的学科路由
- **QA**：检索覆盖核心库 + 补检库，记录降级原因

## 阶段 4：literature_dedup（文献筛选与去重）

- **类型**：按需
- **输入**：catalog.jsonl（多来源文献）
- **输出**：去重后的 catalog.jsonl、dedup-report.md
- **执行方式**：`scripts/dedup.py`
- **QA**：同一 DOI 不重复、预印本不被误删、跨语言重复进入 pending_review

## 阶段 5：deep_reading（深度阅读）

- **类型**：按需
- **输入**：去重后的文献列表
- **输出**：`literature/screening.csv`、每篇的阅读笔记
- **执行方式**：`nature-reader`（逐篇深度阅读，Subagent context: fork）
- **QA**：核心文献均已阅读，screening 决策有依据

## 阶段 6：evidence_matrix（证据矩阵构建）

- **类型**：按需（新增阶段）
- **输入**：深度阅读笔记、screening.csv
- **输出**：`literature/evidence-matrix.csv`、`citations/claim-citation-map.csv`
- **执行方式**：`scripts/evidence_manager.py`
- **QA**：每个论点有支撑文献，evidence-matrix 字段完整

## 阶段 7：research_design（研究设计）

- **类型**：按需
- **输入**：证据矩阵、论文类型
- **输出**：研究方法描述、实验设计方案
- **执行方式**：AI 对话辅助设计
- **QA**：设计可复现，方法描述充分

## 阶段 8：data_analysis（数据、实验或案例分析）

- **类型**：按需（新增适配层）
- **输入**：研究设计、原始数据
- **输出**：分析结果、`analysis/` 目录下的脚本和表格
- **执行方式**：用户自行执行或 AI 辅助脚本
- **QA**：分析可复现，结果记录在 data-dictionary.csv

## 阶段 9：charts_and_tables（图表与结果表制作）

- **类型**：按需
- **输入**：分析结果、数据
- **输出**：`figures/` 和 `tables/` 下的图表文件
- **执行方式**：`nature-figure`（Python 或 R）
- **QA**：图表分辨率达标、编号唯一、配色可辨识

## 阶段 10：outline（提纲设计）

- **类型**：必需
- **输入**：证据矩阵、论文类型
- **输出**：论文提纲（Markdown）
- **执行方式**：`nature-writing` 协助提纲设计
- **QA**：层级合理、逻辑连贯、覆盖所有必需章节

## 阶段 11：writing（分章节撰写）

- **类型**：必需
- **输入**：提纲、证据矩阵、图表
- **输出**：`manuscript/main.md`（或按章节拆分）
- **执行方式**：`nature-writing` 逐章节撰写
- **QA**：[CITE NEEDED] 不残留、图表编号连续、公式语法正确

## 阶段 12：citation_verification（引文核验与补充）

- **类型**：按需
- **输入**：manuscript/main.md、catalog.jsonl、references.bib
- **输出**：验证报告、补充引用
- **执行方式**：`nature-citation` + `scripts/validate_citations.py`
- **QA**：正文引用与 bib 一致、无孤立引用、无伪造引用

## 阶段 13：polishing（内容修改与语言润色）

- **类型**：按需
- **输入**：manuscript/main.md
- **输出**：润色后的源稿
- **执行方式**：`nature-polishing`
- **QA**：术语一致、语法正确、符合目标期刊风格

## 阶段 14：formatting（格式整理与多格式渲染）

- **类型**：按需
- **输入**：润色后的源稿
- **输出**：docx / tex / md 终稿
- **执行方式**：`scripts/render.py` + `scripts/postprocess_docx.py`
- **QA**：validate_docx / validate_tex 通过

## 阶段 15：originality_check（原创性与学术规范检查）

- **类型**：按需
- **输入**：终稿
- **输出**：`outputs/qa/originality-self-audit.md`
- **执行方式**：AI 对话式自查（不提供权威查重）
- **QA**：引用完整、无抄袭段落、数据来源可追溯

## 阶段 16：quality_qa（质量核验与终稿输出）

- **类型**：必需
- **输入**：终稿 + 所有中间产物
- **输出**：QA 报告、outputs/latest/ 终稿
- **执行方式**：`/paper-workflow qa`
- **QA**：所有校验通过，终稿复制到 latest/

## 阶段 17：revision（提交后修改与返修回复）

- **类型**：按需（增强版新增）
- **输入**：审稿意见、终稿
- **输出**：`revision-log.jsonl`、修改后的源稿
- **执行方式**：`nature-response`
- **QA**：逐条回复审稿意见，修改标记清晰

## 回退规则

- **writing → literature_search**：证据不足时定向补检 → 回到 evidence_matrix → 回到 writing
- **revision → polishing**：回复审稿意见后从 polishing 重新走
- **任何阶段 QA 未通过** → 回到该阶段的 in_progress
