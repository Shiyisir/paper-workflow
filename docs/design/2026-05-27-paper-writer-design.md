# AI 自动论文撰写平台 — 设计规格 v4

> 日期：2026-05-27
> 状态：已确认，待实施
> 路径：docs/design/2026-05-27-paper-writer-design.md

---

## 一句话定位

**先做「中文论文 AI 写作工作台」，不是全自动论文平台。** 第一版聚焦核心价值验证：论文项目管理 + 大纲生成 + 逐章撰写 + 中文学术润色 + DOCX 导出 + 日志追踪。

## 技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 | Next.js 15 + TypeScript + Tailwind CSS + Tiptap | App Router，学术风 UI |
| 后端 | FastAPI + Python + SQLAlchemy | AI 接口、SSE、任务编排 |
| 数据库 | SQLite | ORM 天然支持后期切 PostgreSQL |
| AI | DeepSeek (v4-pro/v4-flash) + MiMo (v2.5-pro/v2.5) | 统一 ModelRouter |
| 导出 | python-docx（DOCX）+ 直出（Markdown） | PDF/Pandoc 后置 |
| 流式 | SSE | 后端→前端实时推流 |

## 三阶段路线图

### Phase 1：中文论文写作工作台（MVP）

**目标：跑通「新建论文→大纲→撰写→润色→导出」闭环**

包含：
- 论文项目管理（新建/列表/详情）
- AI 生成大纲 + 用户编辑
- 按章节逐章 AI 撰写 + 人工审核
- 中文学术润色（5 种模式）
- 导出 Markdown + DOCX
- generation_logs 追踪
- API Key 管理 + 模型路由
- 底部状态栏（进度 + token）

不包含：
- ❌ CNKI / PubMed / CrossRef 自动检索
- ❌ PDF 导出 + Pandoc
- ❌ GB/T 7714 CSL 联动
- ❌ PDF 上传解析

文献输入方式：用户手动粘贴/录入文献信息（标题、作者、摘要），系统存入 literature 表，撰写时作为参考上下文。

### Phase 2：文献管理 + 参考文献

- 上传 PDF/DOCX → PyMuPDF 提取标题/摘要/作者
- 手动录入 DOI → CrossRef/PubMed 自动补全英文文献
- 参考文献列表管理（选择、排序、标注）
- GB/T 7714 参考文献格式化
- 导出时自动生成参考文献列表

### Phase 3：CNKI 兼容 + 高级导出

- 知网题录导入（用户从知网导出 RIS/EndNoteXML → 系统导入）
- 知网 PDF/CAJ 上传解析
- 浏览器自动化检索 CNKI（最后考虑，涉及登录/反爬/合规）
- PDF 导出（Pandoc + LaTeX）
- 更多 CSL 样式扩展

---

## Phase 1 数据库模型

### papers
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| title | string | 论文标题 |
| type | enum | experimental / review |
| field | string | 研究领域 |
| core_question | string | 核心问题 |
| target_journal | string? | 目标期刊 |
| target_audience | string | 目标读者 |
| language | enum | zh / en，默认 zh |
| word_count_target | int? | 预估字数 |
| writing_style | string? | 写作风格 |
| status | enum | draft / active / completed / archived |
| created_at | datetime | |
| updated_at | datetime | |

### stages（可配置工作流）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| paper_id | FK → papers | |
| stage_name | string | 不固定编号，用 stage_order 排序 |
| stage_order | int | 不同论文类型可配不同工作流阶段 |
| status | enum | pending / running / review / approved / failed / regenerated |
| output_data | JSON | 阶段产出 |
| review_notes | string? | 用户审核备注 |
| retry_count | int | 重试次数 |
| error_message | string? | 失败信息 |
| created_at | datetime | |
| updated_at | datetime | |

### literature（Phase 1 仅手动录入）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| paper_id | FK → papers | |
| source | enum | manual（Phase 1 只有 manual） |
| title | string | |
| authors | JSON | ["Author A", "Author B"] |
| journal | string? | |
| year | int? | |
| abstract | string? | |
| doi | string? | |
| selected | boolean | 用户是否保留 |
| relevance_note | string? | AI 标注的相关性说明 |
| created_at | datetime | |

### manuscript_sections（markdown 为主）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| paper_id | FK → papers | |
| section_type | string | abstract / introduction / methods / results / discussion / conclusion |
| title | string | 章节标题 |
| markdown_text | text | **主存储** |
| tiptap_json | JSON | 编辑器状态，不单独存储 html_content |
| version | int | 版本号 |
| ai_generated | boolean | |
| reviewed | boolean | 用户是否已审核 |
| order_index | int | 排序 |
| created_at | datetime | |
| updated_at | datetime | |

> html_content 不单独存储，导出时从 markdown_text 临时生成，避免三份内容不同步。

### generation_logs（可追溯）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| paper_id | FK → papers | |
| section_id | FK? → manuscript_sections | |
| stage_id | FK? → stages | |
| model_id | string | 使用的模型 ID |
| task_type | string | writing / outline / polish / search / format / reasoning |
| prompt_text | text | 发送给模型的 prompt |
| input_text | text | 输入文本 |
| output_text | text | 模型输出 |
| token_input | int | 输入 token 数 |
| token_output | int | 输出 token 数 |
| accepted | bool? | 用户是否采纳 |
| user_modified | bool? | 用户是否修改了输出 |
| created_at | datetime | |

### api_keys（本地加密存储）
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID | 主键 |
| provider | enum | deepseek / mimo |
| key_encrypted | text | AES-256 (Fernet) 加密 |
| task_type | string? | writing / search / outline / polish / format / reasoning |
| is_default | boolean | 是否默认 |

> 加密方案：后端用 cryptography 库的 Fernet 对称加密，密钥存在环境变量 APP_SECRET_KEY 中。

---

## Phase 1 页面设计（4 页 + 状态栏）

### `/` 首页 Dashboard
- 论文卡片网格：标题、类型标签、阶段进度条、最后更新时间
- 右上角「+ 新建论文」+ 设置齿轮
- 空状态引导

### `/papers/new` 新建论文
- 表单：标题、类型（实验型/综述型）、研究领域、核心问题、目标期刊（选填）、目标读者、语言（默认中文）、预估字数
- 「开始 AI 撰写」按钮

### `/papers/[id]` 论文详情
- 顶部信息卡
- 阶段流水线指示器（可配置阶段，当前阶段高亮，状态图标）
- 各阶段操作区：
  - 大纲：树形编辑
  - 文献：手动录入表单（标题/作者/摘要/DOI）
  - 撰写：章节卡片 → 进入写作台
  - 润色：diff 对比
  - 导出：Markdown / DOCX

### `/papers/[id]/write` 写作工作台
- 三栏：左=章节导航，中=Tiptap 编辑器，右=AI 面板（重生成/润色/补引文）
- 版本切换、字数统计
- 底部状态栏：当前模型、生成进度、token 消耗

### `/settings` 设置
- DeepSeek Key + MiMo Key（加密存储）
- 按 6 种任务分配模型（下拉选择 4 个模型）
- 测试连接 + token 统计

---

## 学术风 UI 规范

- 标题：Noto Serif SC / Libre Baskerville（衬线）
- 正文：Inter / Noto Sans SC
- 背景：`#FAF7F0` 米白
- 正文色：`#2D3748` 深灰
- 主色：`#1A365D` 学术深蓝
- 辅助：`#276749` 深绿（完成状态）
- 失败：`#9B2C2C` 暗红
- 审核中：`#B7791F` 暗黄
- 卡片：白色/浅米色，1px 细边框，极浅阴影，4px 圆角
- 风格：大量留白，像学术期刊网站，不是 SaaS 后台

---

## 中文学术润色（5 种模式）

| 模式 | 说明 |
|---|---|
| `academic_zh` | 学术化：去口语、书面化、规范术语 |
| `logic` | 逻辑衔接：段落过渡、因果链、论证层次 |
| `normalize` | 术语规范化：同一概念统一用词 |
| `journal` | 期刊风格适配 |
| `reduce_ai_style` | 降低 AI 痕迹：去过度整齐、去转折词堆砌、减少句式重复、去掉空泛表达 |

用 DeepSeek V4 Pro + 自建 prompt 模板实现。prompt 存 `backend/app/services/polish/prompts/`。

---

## AI 模型路由

| 任务类型 | 默认模型 | 说明 |
|---|---|---|
| writing（正文撰写） | deepseek-v4-pro | 长文本、高质量 |
| outline（大纲生成） | deepseek-v4-pro | 结构推理 |
| polish（润色） | deepseek-v4-pro | 表达精炼 |
| search（文献处理） | deepseek-v4-flash | 快速、批量 |
| format（格式化/分类） | mimo-v2.5 | 轻量任务 |
| reasoning（推理分析） | mimo-v2.5-pro | 深度推理 |

每次调用写入 generation_logs。用户可在设置页按任务覆盖模型。

---

## API 接口（FastAPI）

### 论文管理
- `POST /api/papers` — 创建论文
- `GET /api/papers` — 列表
- `GET /api/papers/{id}` — 详情（含阶段状态）
- `PATCH /api/papers/{id}` — 更新
- `DELETE /api/papers/{id}` — 删除

### 写作流水线（SSE 流式）
- `POST /api/papers/{id}/pipeline/outline` — 生成大纲
- `POST /api/papers/{id}/pipeline/draft` — 逐章撰写
- `POST /api/papers/{id}/pipeline/polish` — 润色（body: { section_id, mode }）

### 文献
- `GET /api/papers/{id}/literature` — 获取文献列表
- `POST /api/papers/{id}/literature` — 手动添加文献
- `PATCH /api/literature/{id}` — 更新
- `DELETE /api/literature/{id}` — 删除

### 章节
- `GET /api/papers/{id}/sections` — 获取所有章节
- `PATCH /api/sections/{id}` — 编辑章节内容
- `POST /api/sections/{id}/regenerate` — AI 重新生成

### 导出
- `POST /api/papers/{id}/export` — 导出（body: { format: "markdown" | "docx" }）

### 日志
- `GET /api/papers/{id}/logs` — 生成历史

### 设置
- `GET /api/settings/keys` — 获取已配置 key（脱敏）
- `POST /api/settings/keys` — 添加/更新 key
- `POST /api/settings/test` — 测试 key 有效性
- `GET /api/settings/stats` — token 消耗统计

---

## 目录结构

```
论文工作流/
├─ web/
│  ├─ frontend/               ← Next.js
│  │  ├─ src/app/
│  │  │  ├─ page.tsx          ← Dashboard
│  │  │  ├─ papers/
│  │  │  │  ├─ new/page.tsx
│  │  │  │  └─ [id]/
│  │  │  │     ├─ page.tsx    ← 论文详情
│  │  │  │     └─ write/page.tsx ← 写作台
│  │  │  └─ settings/page.tsx
│  │  ├─ src/components/
│  │  │  ├─ dashboard/        ← 论文卡片
│  │  │  ├─ pipeline/         ← 阶段指示器
│  │  │  ├─ editor/           ← Tiptap + AI 面板
│  │  │  └─ common/           ← 通用组件
│  │  ├─ src/lib/             ← API 客户端
│  │  ├─ src/hooks/           ← SSE hook
│  │  └─ package.json
│  ├─ backend/                ← FastAPI
│  │  ├─ app/
│  │  │  ├─ api/              ← 路由
│  │  │  ├─ services/
│  │  │  │  ├─ ai/            ← ModelRouter + 客户端
│  │  │  │  ├─ pipeline/      ← 工作流引擎
│  │  │  │  ├─ polish/        ← 5 种润色 prompt
│  │  │  │  └─ export/        ← Markdown + DOCX
│  │  │  ├─ models/           ← SQLAlchemy
│  │  │  ├─ schemas/          ← Pydantic
│  │  │  ├─ db/               ← 数据库连接
│  │  │  └─ main.py
│  │  ├─ data/                ← SQLite + 上传文件
│  │  ├─ requirements.txt
│  │  └─ .env.example         ← APP_SECRET_KEY
│  └─ README.md
├─ [原有文件不动]
```

---

## Phase 1 实施计划（8 步）

| 步 | 内容 | 可验证标准 |
|---|---|---|
| 1 | 后端骨架：FastAPI + SQLAlchemy + SQLite + CRUD API | Postman 能跑通论文 CRUD |
| 2 | 前端骨架：Next.js + Tailwind 学术风 + 4 页路由 | 浏览器看到 4 个页面 |
| 3 | 首页 Dashboard + 新建论文 | 能创建论文、看到列表 |
| 4 | AI 服务层：ModelRouter + DeepSeek/MiMo + SSE | 能流式调用模型并返回文本 |
| 5 | 大纲生成 + 树形编辑器 | 输入论文信息 → AI 生成大纲 → 可编辑 |
| 6 | 写作工作台：Tiptap + 逐章生成 + 人工审核 | 按大纲逐章生成、可编辑、可审核 |
| 7 | 中文学术润色：5 种模式 + diff 视图 | 选中章节 → 选模式 → 展示 diff |
| 8 | 导出 + 设置页 + 状态栏 + 日志 | 能下载文件、配置 key、查看 token |

---

## 假设与风险

- DeepSeek API 兼容 OpenAI SDK（base_url: https://api.deepseek.com）
- MiMo API 格式需实现时验证
- MVP 不做用户认证（本地单用户）
- API Key 用 Fernet 加密存 SQLite，密钥在 .env 的 APP_SECRET_KEY
- stages 不固定编号，支持不同论文类型配不同工作流
- html_content 不单独存，导出时从 markdown 生成
- CNKI / PubMed / CrossRef 全部后置，Phase 1 文献纯手动录入
- 中文学术润色 prompt 需要反复迭代调优
