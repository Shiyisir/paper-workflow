# paper-workflow — 论文写作编排器设计文档

> 状态：已批准 | 日期：2026-06-12 | 版本：v1.0

## 1. 总体架构与边界

### 1.1 定位

`paper-workflow` 是论文写作工作流的唯一编排入口。它不实现任何学术能力（搜索/阅读/写作/润色/引用），只负责：收集需求 → 按阶段路由 → 调叶子 skill → 质量核验 → 推进到下一阶段。

### 1.2 核心约束

- **单一总路由**：`nature-paper` 从路由链移除，`paper-workflow` 直接调用叶子 skill
- **双模式**：项目模式（命令手动启动）+ 单次任务（自然语言触发叶子 skill）
- **状态可恢复**：所有进度落盘到 `.paper-workflow/state.yaml`，会话重启后 `/paper-workflow resume` 恢复
- **不替代学术判断**：AI 辅助执行，最终学术决策由人做出

### 1.3 叶子 skill 调用关系

```
paper-workflow（唯一编排层）
    ├── nature-academic-search   ← 英文文献搜索
    ├── cnki-search              ← 中文文献搜索
    ├── cnki-export              ← 文献导出
    ├── cnki-download            ← PDF 下载
    ├── nature-reader            ← 深度阅读（Subagent，context: fork）
    ├── nature-writing           ← 撰写章节
    ├── nature-figure            ← 图表制作
    ├── nature-citation          ← 引文核验
    ├── nature-polishing         ← 语言润色
    ├── nature-reviewer          ← 投稿前预审（Subagent）
    ├── nature-response          ← 审稿回复
    └── nature-data              ← Data Availability Statement
```

### 1.4 Skill / Subagent / Script / Hook 职责边界

| 机制 | 承担任务 | 示例 |
|------|----------|------|
| **Skill** | 可复用操作流程 | nature-writing, nature-figure, nature-polishing |
| **Subagent** | 长上下文任务，隔离执行 | 逐篇深度阅读（context: fork）、投稿前预审、多文献对比 |
| **Script** | 确定性逻辑，保证幂等 | dedup.py, render.py, validate_*.py, workflow_state.py |
| **Hook** | 二次兜底校验 | 终稿输出后自动运行 validate_manuscript.py |

### 1.5 禁止事项

- Subagent 不得嵌套派生下一级 Subagent。多文献并行阅读由 `paper-workflow` 总控分发
- 写作阶段不得使用未进入证据矩阵的文献生成引用。缺证据时使用 `[CITE NEEDED]` 占位符
- 不得声称提供权威重复率检测
- 自然语言对话中不得自动加载完整工作流（`disable-model-invocation: true`）

---

## 2. 完整目录结构

### 2.1 工作流程序本体

```
.claude/skills/paper-workflow/
├── SKILL.md                            ← ~100行，入口路由 + 核心命令
├── references/
│   ├── lifecycle.md                    ← 17阶段详细说明
│   ├── routing-rules.md                ← 状态机、跳转、回退规则
│   ├── type-matrix.md                  ← 论文类型 × 阶段矩阵
│   ├── defaults.md                     ← 默认值、检索模式、字数范围
│   ├── search-profiles.md              ← 学科 → 数据库组合路由表
│   ├── evidence-schema.md              ← 证据矩阵与命题-引文映射 schema
│   ├── quality-checklist.md            ← 每阶段质量检查项
│   ├── pandoc-workflow.md              ← 渲染流程、命令模板
│   └── latex-gotchas.md                ← 按 profile 分层的避坑规则
├── schemas/
│   ├── workflow-state.schema.json
│   ├── literature-record.schema.json
│   └── render-profile.schema.json
├── scripts/
│   ├── workflow_state.py               ← 初始化/读取/更新 state.yaml
│   ├── dedup.py                        ← 去重 + 来源合并 + 版本关联
│   ├── validate_manuscript.py          ← 检查 Markdown/LaTeX 源稿结构
│   ├── validate_citations.py           ← 正文引用 ↔ 参考文献一致性
│   ├── validate_docx.py                ← 检查生成后 Word 文档
│   ├── validate_tex.py                 ← 检查生成后 LaTeX 文件
│   ├── render.py                       ← 统一渲染入口
│   └── postprocess_docx.py             ← Word 后处理（幂等，配置驱动）
├── templates/
│   ├── profiles/
│   │   ├── course-cn.yaml
│   │   ├── thesis-cn.yaml
│   │   ├── journal-word.yaml
│   │   └── journal-latex.yaml
│   ├── docx/
│   │   ├── course-cn-reference.docx
│   │   ├── thesis-cn-reference.docx
│   │   └── journal-word-reference.docx
│   ├── latex/
│   │   └── journal.tex
│   └── csl/
│       ├── gb-t-7714.csl
│       ├── apa.csl
│       └── chicago.csl
└── tests/
    ├── fixtures/
    │   ├── formulas.md
    │   ├── tables.md
    │   ├── figures.md
    │   ├── citations.md
    │   └── chinese-headings.md
    └── test_render.py
```

### 2.2 论文项目运行时目录

每篇论文根目录下生成：

```
<paper-project>/
├── .paper-workflow/
│   ├── state.yaml              ← 当前阶段、状态、依赖、产物
│   ├── config.yaml             ← 论文类型、语言、学科、引用格式
│   ├── artifact-manifest.jsonl ← 所有成果文件版本与状态
│   ├── search-log.jsonl        ← 每次检索记录
│   └── revision-log.jsonl      ← 导师/审稿意见与修改记录（增强版）
├── manuscript/
│   └── main.md                 ← 论文源稿（或按章节拆分）
├── literature/
│   ├── catalog.jsonl           ← 完整文献元数据 + 来源 + 去重关系
│   ├── screening.csv           ← 筛选记录
│   ├── evidence-matrix.csv     ← 文献 → 论据映射
│   ├── references.bib          ← BibTeX 参考文献库
│   └── references.csl.json     ← CSL JSON 参考文献库
├── citations/
│   └── claim-citation-map.csv  ← 论点 → 引文映射
├── analysis/
│   ├── README.md
│   ├── data-dictionary.csv
│   ├── analysis-plan.md
│   ├── scripts/
│   ├── tables/
│   ├── figures/
│   └── logs/
├── figures/
├── tables/
└── outputs/
    ├── thesis-v001.docx
    ├── thesis-v002.docx
    ├── thesis-v003.pdf
    ├── latest/
    │   └── thesis.docx          ← 仅通过 QA 后复制
    └── qa/
        ├── thesis-v003-validation.md
        ├── thesis-v003-citations.md
        └── originality-self-audit.md
```

---

## 3. 命令接口

### 3.1 核心命令

| 命令 | 功能 | 前置条件 |
|------|------|----------|
| `/paper-workflow init` | 初始化新项目：交互式提问 → 写 config.yaml + state.yaml | 在论文根目录执行 |
| `/paper-workflow status` | 展示当前阶段、已完成阶段、产物列表、下一步建议 | state.yaml 存在 |
| `/paper-workflow resume` | 从 state.yaml 恢复，进入当前 in_progress 阶段 | state.yaml 存在 |
| `/paper-workflow run <stage>` | 推进指定阶段到 done（自动满足依赖） | 阶段为 pending 或 in_progress |
| `/paper-workflow run <stage> --override` | 跳过依赖检查强制执行，写入操作日志 | — |
| `/paper-workflow qa` | 对当前阶段产物运行质量核验 | 当前阶段为 done |
| `/paper-workflow render <profile>` | 用指定 profile 输出终稿 | manuscript/main.md 存在 |
| `/paper-workflow render <profile> --dry-run` | 预览渲染将执行的操作，不实际生成文件 | — |
| `/paper-workflow revise` | 进入投稿返修模式（增强版） | 终稿已输出 |

### 3.2 单次任务（自然语言触发，不走工作流）

| 用户输入 | 直接路由到 |
|----------|-----------|
| "搜知网储能论文" | cnki-search |
| "search PubMed for perovskite" | nature-academic-search |
| "润色这段摘要" | nature-polishing |
| "读这篇论文" | nature-reader |
| "核验这篇的引用" | nature-citation |
| "画这张图" | nature-figure |
| "模拟审稿" | nature-reviewer |
| "回复审稿意见" | nature-response |

### 3.3 阶段标识符

`/paper-workflow run` 接受的阶段名：

```
requirements, material_prep, literature_search, literature_dedup,
deep_reading, evidence_matrix, research_design, data_analysis,
charts_and_tables, outline, writing, citation_verification,
polishing, formatting, originality_check, quality_qa, revision
```

---

## 4. 状态机 Schema 与依赖图

### 4.1 state.yaml Schema

```yaml
schema_version: 1
project_id: <slug>                         # 唯一标识
paper_type: <course_paper|thesis|proposal|literature_review|
            lab_report|data_report|survey_report|journal_article|
            book_report|project_proposal|policy_report>
research_type: <theoretical|review|empirical|experimental|case|survey>
discipline: <humanities|social_science|economics_management|
             engineering|medicine|computer_science|interdisciplinary>
language: <zh|en|bilingual>
target_journal: <null|string>
current_stage: <stage_id>

stages:
  <stage_id>:
    status: <pending|in_progress|done|skipped|blocked>
    depends_on: [<stage_id>, ...]
    started_at: <null|ISO8601>
    completed_at: <null|ISO8601>
    qa_status: <pending|passed|failed|overridden>
    qa_report: <null|path>
    artifacts: [<path>, ...]
    blockers: [<string>, ...]
```

### 4.2 阶段依赖图

```
requirements ─────────────────────────────────────────────────────┐
    │                                                              │
    ├── material_prep ─────────────────────────────────────────┐   │
    │                                                           │   │
    ├── literature_search ──→ literature_dedup                  │   │
    │         │                    │                            │   │
    │         │                    ├── deep_reading             │   │
    │         │                    │       │                    │   │
    │         │                    │       └── evidence_matrix  │   │
    │         │                    │               │            │   │
    │         │                    │               ├── research_design
    │         │                    │               │       │     │   │
    │         │                    │               │       ├── data_analysis
    │         │                    │               │       │       │
    │         │                    │               │       │       ├── charts_and_tables
    │         │                    │               │       │       │       │
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
              │                    │                       │       │       │       │       │       │
              └────────────────────┴───────────────────────┴───────┴───────┴───────┴───────┴─── revision

回退规则：
- writing（讨论章）：证据不足 → literature_search（定向补检）→ evidence_matrix → 回 writing
- revision：回复审稿意见后修改 → 从 polishing 开始重走
- 任何阶段 QA 未通过 → 回到该阶段的 in_progress 状态
```

### 4.3 阶段跳过逻辑

根据 paper_type + research_type，`/paper-workflow init` 自动标记跳过：

| 论文类型 | 自动跳过 |
|----------|----------|
| 读书报告 | literature_search, dedup, deep_reading, evidence_matrix, research_design, data_analysis, charts_and_tables |
| 文献综述 | data_analysis, charts_and_tables |
| 实验报告 | literature_search（可选）, deep_reading（可选） |
| 理论型投稿 | data_analysis（如有则保留） |

### 4.4 workflow_state.py 规则

- `set_stage_done(stage_id)`：验证 depends_on 全部 done → 设置 done；否则 → 设置 blocked，输出缺失条件
- `set_stage_done(stage_id, override=True)`：跳过依赖检查，写入操作日志到 state.yaml 的 `overrides` 字段
- `get_next_stages()`：返回所有 depends_on 已满足且 status 为 pending 的阶段列表
- `mark_stage_blocked(stage_id, reason)`：记录 blockers

---

## 5. 文献记录、证据矩阵与引文映射 Schema

### 5.1 catalog.jsonl（每行一条文献）

```json
{
  "canonical_id": "ref-0001",
  "citekey": "wang2024RockyDesertification",
  "title": "Rocky desertification impacts on ecosystem services in karst regions",
  "authors": ["Wang, X.", "Li, Y.", "Zhang, H."],
  "year": 2024,
  "doi": "10.1016/j.ecoser.2024.101650",
  "journal": "Ecosystem Services",
  "volume": "68",
  "pages": "101650",
  "abstract": "...",
  "keywords": ["rocky desertification", "ecosystem services", "karst"],
  "language": "en",
  "sources": ["scopus", "crossref"],
  "fulltext_available": true,
  "fulltext_path": "literature/papers/wang2024.pdf",
  "related_versions": [
    {"source": "arxiv", "id": "2401.12345", "relation": "preprint_of"}
  ],
  "screening_status": "included",
  "screening_notes": "核心文献，直接支撑研究区定义"
}
```

### 5.2 evidence-matrix.csv

| 字段 | 类型 | 说明 |
|------|------|------|
| ref_citekey | string | 文献 citekey |
| topic | string | 研究主题 |
| region | string | 研究区/对象 |
| data_source | string | 数据来源 |
| method | string | 方法 |
| key_finding | string | 关键结论/摘录 |
| limitation | string | 局限性 |
| usable_sections | string | 可用于哪些章节（逗号分隔） |
| page_ref | string | 原文页码/段落 |

### 5.3 claim-citation-map.csv

| 字段 | 类型 | 说明 |
|------|------|------|
| claim_id | string | 论点编号（C001, C002, ...） |
| section | string | 所属章节 |
| claim | string | 待表达命题 |
| supporting_refs | string | 支撑文献 citekey（逗号分隔） |
| strength | enum | strong / medium / weak |
| verified | enum | yes / pending / no |

### 5.4 引用规则

- 正文引用使用稳定 citekey（`[@wang2024RockyDesertification]`），不使用 `canonical_id`（`ref-0001`）
- `references.bib` 和 `references.csl.json` 作为参考文献单一事实来源，citekey 保持一致
- 写作阶段仅允许使用已进入 evidence-matrix.csv 且 usable_sections 匹配当前章节的文献
- 无法核验的观点写 `[CITE NEEDED]`，由 citation_verification 阶段统一处理

---

## 6. 检索 Profile 与能力降级

### 6.1 数据库角色划分

| 数据库 | 角色 | 适用条件 |
|--------|------|----------|
| CNKI | 中文核心库 | 中国语境、中文论文、区域/政策研究 |
| Scopus | 英文综合核心库 | 有 API 权限 |
| PubMed | 条件库：医学/生命科学 | 医学、生物、公共卫生 |
| arXiv | 条件库：前沿预印本 | 计算机、数学、物理、统计、AI、部分经济学 |
| Crossref | 元数据补全库 | DOI 补全、题名核验、去重 |
| ScienceDirect | 全文补充库 | 目标文章来自 Elsevier 平台 |

### 6.2 学科路由表（`references/search-profiles.md`）

| 学科方向 | 默认数据库组合 |
|----------|---------------|
| 人文、民族学 | CNKI + Scopus（英文综合）；不启 PubMed 和 arXiv |
| 社科、经管 | CNKI + Scopus；计量研究可选 arXiv |
| 生态环境、地理 | CNKI + Scopus + Crossref；按主题选 ScienceDirect |
| 医学、生物 | PubMed + Scopus + Crossref；按需补 ScienceDirect |
| 计算机、AI、统计 | Scopus + arXiv + Crossref |
| 工科 | Scopus + Crossref + ScienceDirect；按主题选 arXiv |

### 6.3 检索模式

| 模式 | 适用场景 | 初筛规模 | 深度阅读 |
|------|----------|:---:|:---:|
| quick | 课程论文、快速补充引用 | 15–30 条 | 5–10 篇 |
| standard | 学位论文、普通投稿 | 40–100 条 | 10–30 篇 |
| systematic | 系统综述、证据综述 | 不固定 | 按纳排标准筛选 |

### 6.4 能力降级

`config.yaml` 记录实际可用能力：

```yaml
search_capabilities:
  cnki_search: available
  cnki_download: available
  scopus: unavailable
  crossref: available
  pubmed: available
  arxiv: available
  sciencedirect: browser_only
```

降级规则：理想组合中某库不可用 → 记录降级原因到 search-log.jsonl → 使用可用库补搜索 + Crossref 补元数据。不自带静默失败。

### 6.5 检索流程

```
第一轮：核心关键词检索（主要库）
→ 标题与摘要初筛 → screening.csv
第二轮：同义词、缩写、近义概念补检
第三轮：针对论证缺口定向补检
第四轮（可选）：参考文献追溯
→ PDF 下载只放在摘要初筛后，不通篇批量下载
```

---

## 7. 渲染 Profile 与 QA 流程

### 7.1 渲染 Profile 示例

```yaml
# templates/profiles/thesis-cn.yaml
output: docx
reference_doc: templates/docx/thesis-cn-reference.docx
csl: templates/csl/gb-t-7714.csl
number_sections: false
native_math: omml
convert_svg_to: png
toc: true
toc_depth: 3
caption_style: chinese
postprocess: true
```

```yaml
# templates/profiles/journal-latex.yaml
output: tex
latex_template: templates/latex/journal.tex
csl: templates/csl/apa.csl
number_sections: true
native_math: latex
convert_svg_to: pdf
toc: false
postprocess: false
```

### 7.2 渲染链（render.py 内部）

```
1. validate_manuscript.py  ← 检查源稿
2. pandoc + citeproc       ← 核心转换
3. SVG 转换                ← SVG → PNG/PDF
4. postprocess_docx.py     ← Word 后处理（仅 docx profile）
5. validate_docx.py 或 validate_tex.py  ← 检查输出文件
6. 输出 QA 报告
```

**`render.py --dry-run`**：输出即将执行的全部操作，不生成文件。

### 7.3 规避规则（按 profile 分层）

| 规则 | profile 范围 | 说明 |
|------|-------------|------|
| 禁用 `\tag{}` | docx-safe | pandoc 转 OMML 时报未知控制序列 |
| 禁止 Unicode 下标 | 全局 | Arial 缺字；用 `$n_1$` |
| `\newline` 不在标题中 | 全局 | 导致 pandoc 标题解析错误 |
| `--number-sections` | profile 开关 | 中文报告关，英文期刊开 |
| YAML frontmatter | 全局 | 使用独立 `metadata.yaml`，避免误生成标题页 |

### 7.4 输出版本化

```
outputs/
├── thesis-v001.docx
├── thesis-v002.docx
├── thesis-v003.pdf
├── latest/
│   └── thesis.docx          ← 仅通过 QA 后复制
└── qa/
    ├── thesis-v003-validation.md
    ├── thesis-v003-citations.md
    └── originality-self-audit.md
```

---

## 8. 脚本职责及函数接口

### 8.1 workflow_state.py

```python
def init_state(project_id: str, config: dict) -> dict:
    """创建 state.yaml + config.yaml，标记自动跳过阶段"""

def load_state() -> dict:
    """读取 state.yaml 和 config.yaml"""

def set_stage_status(stage_id: str, status: str, override: bool = False):
    """更新阶段状态。override=True 跳过依赖检查，写入 overrides 日志"""

def get_next_stages() -> list[str]:
    """返回 depends_on 满足且 status=pending 的阶段"""

def get_blocked_stages() -> list[dict]:
    """返回 status=blocked 的阶段及其缺失条件"""

def mark_artifact(artifact: dict):
    """追加记录到 artifact-manifest.jsonl"""

def update_qa_status(stage_id: str, qa_status: str, qa_report: str):
    """更新阶段 QA 状态"""
```

### 8.2 dedup.py

```python
def normalize_doi(raw: str) -> str | None:
    """统一 DOI 为 10.xxxx/... 格式"""

def deduplicate(records: list[dict]) -> dict:
    """
    返回:
    {
        "unique": [...],              # 去重后唯一记录
        "merged": [...],              # 来源合并的记录
        "related": [...],             # 关联版本（预印本/正式版）
        "pending_review": [...]       # 需人工判定的疑似重复
    }
    """
```

去重优先级：
1. DOI 规范化精确匹配
2. 标准化标题完全一致 + 年份一致
3. 标题高相似度 + 第一作者一致 + 年份差 ≤ 1
4. 作者组匹配 + 期刊 + 卷期页码一致
5. 跨语言标题或预印本 → 标记 related_versions，不删除

### 8.3 validate_manuscript.py

```python
def validate_structure(md_path: str) -> dict:
    """检查标题层级、图表编号连续性、[CITE NEEDED] 残留"""

def validate_formulas(md_path: str) -> dict:
    """检查 \tag{} 违规、Unicode 下标、公式括号匹配"""

def validate_attachments(md_path: str, figures_dir: str) -> dict:
    """检查所有引用的图片文件是否存在"""
```

### 8.4 validate_citations.py

```python
def check_citekey_consistency(manuscript_path: str, bib_path: str) -> dict:
    """检查正文 citekey 是否在 .bib 中存在，有无孤立文献"""

def check_duplicate_citekeys(bib_path: str) -> list:
    """检测重复 citekey"""

def cross_check_citations(manuscript_path: str, claim_map_path: str) -> dict:
    """正文引用 ↔ claim-citation-map.csv 交叉校验"""
```

### 8.5 validate_docx.py

```python
def validate_docx(docx_path: str) -> dict:
    """检查：文件可打开、标题样式正确、公式为 OMML 对象、图表编号、字体、表格边框"""
```

### 8.6 validate_tex.py

```python
def validate_tex(tex_path: str) -> dict:
    """检查：模板引用、图片路径、引用库、常见编译风险"""
```

### 8.7 render.py

```python
def render(profile: str, input_md: str, output_path: str, dry_run: bool = False):
    """
    渲染链：
    validate_manuscript → pandoc+citeproc → SVG转换
    → postprocess_docx（仅docx） → validate_docx/tex → QA报告
    """
```

### 8.8 postprocess_docx.py

要求：幂等（重复运行不产生编号叠加/边框加粗/页边距漂移）；样式优先从 `reference.docx` 继承，脚本只处理 pandoc 已知 bug（MS Gothic → 宋体、三线表边框、图表自动编号）。

---

## 9. Hook 配置

### 9.1 触发条件

在项目 `.claude/settings.json` 中配置：

```json
{
  "hooks": {
    "post_tool_use": [
      {
        "matcher": "Bash",
        "trigger": "render.py",
        "command": "python .claude/skills/paper-workflow/scripts/validate_manuscript.py manuscript/main.md"
      }
    ]
  }
}
```

### 9.2 职责

- Hook 仅为**二次保险**：当用户绕过 `render.py` 手动修改输出文件时检测异常
- 核心渲染检查已内置于 `render.py`，不依赖 Hook
- Hook 不阻止操作，仅输出警告

---

## 10. MVP 开发顺序与测试清单

### MVP（第一版）

#### 必须实现

| 优先级 | 模块 | 内容 |
|:---:|------|------|
| 1 | SKILL.md | 入口 + 核心命令 + 触发条件 + 各阶段执行器映射 |
| 2 | schemas/ | workflow-state.schema.json, literature-record.schema.json, render-profile.schema.json |
| 3 | workflow_state.py | init/load/set_stage_status/get_next_stages/mark_artifact |
| 4 | state.yaml + config.yaml | 项目初始化自动生成 |
| 5 | artifact-manifest.jsonl | 成果追踪 |
| 6 | dedup.py | DOI 规范 + 去重 + 来源合并 + 版本关联 |
| 7 | search-profiles.md + config.yaml search_capabilities | 学科路由 + 能力探测 |
| 8 | evidence-matrix.csv + claim-citation-map.csv | 证据矩阵构建 |
| 9 | references.bib + references.csl.json | 正式参考文献库 |
| 10 | render.py | 统⼀渲染入口 + --dry-run |
| 11 | postprocess_docx.py | Word 后处理（幂等，从你的实验报告项目升级） |
| 12 | validate_manuscript.py | 源稿结构、图表编号、公式语法 |
| 13 | validate_citations.py | 正文引用 ↔ 文献库一致性 |
| 14 | validate_docx.py | Word 文档检查 |
| 15 | validate_tex.py | LaTeX 文件检查 |
| 16 | 三个渲染 profile | thesis-cn, journal-latex, markdown-draft |
| 17 | tests/fixtures/ + test_render.py | 渲染回归测试 |
| 18 | references/lifecycle.md | 17 阶段详细说明 |

#### MVP 支持的命令

```
/paper-workflow init|status|resume|run <stage>|qa|render <profile>
```

#### MVP 支持的输出格式

```
Word: thesis-cn（中文论文/学位论文）
LaTeX: journal-latex（英文投稿）
Markdown: markdown-draft（快速草稿）
```

### 增强版（第二版）

- revision-log.jsonl + `/paper-workflow revise`
- systematic 检索模式
- 更多学校 Word 模板 / 更多期刊 LaTeX 模板
- 批量 PDF 下载
- Subagent 并行深度阅读
- Hook 二次校验
- 完整数据分析适配器
- 更多 CSL 引用格式

---

## 附录：17 阶段完整清单

| 编号 | 阶段 | 英文标识 | 类型 |
|:---:|------|----------|------|
| 1 | 需求确认 | requirements | 必需 |
| 2 | 材料准备 | material_prep | 按需 |
| 3 | 文献检索 | literature_search | 按需 |
| 4 | 文献筛选与去重 | literature_dedup | 按需 |
| 5 | 深度阅读 | deep_reading | 按需 |
| 6 | 证据矩阵构建 | evidence_matrix | 按需（新增） |
| 7 | 研究设计 | research_design | 按需 |
| 8 | 数据、实验或案例分析 | data_analysis | 按需（新增适配层） |
| 9 | 图表与结果表制作 | charts_and_tables | 按需 |
| 10 | 提纲设计 | outline | 必需 |
| 11 | 分章节撰写 | writing | 必需 |
| 12 | 引文核验与补充 | citation_verification | 按需 |
| 13 | 内容修改与语言润色 | polishing | 按需 |
| 14 | 格式整理与多格式渲染 | formatting | 按需 |
| 15 | 原创性与学术规范检查 | originality_check | 按需 |
| 16 | 质量核验与终稿输出 | quality_qa | 必需 |
| 17 | 提交后修改与返修回复 | revision | 按需（新增） |
