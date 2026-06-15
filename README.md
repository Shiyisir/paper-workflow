# 论文工作流

学术写作工作台。`paper-workflow` 是编排层，管理论文项目从初始化到终稿输出的完整生命周期；搜索、阅读、写作、润色等重任务交给叶子 skill。

## 快速理解

| 文件 | 给谁 | 内容 |
|------|------|------|
| `README.md` | 人 | 项目入口、安装、常用命令 |
| `AGENTS.md` | AI | 行为规则、红线、修改规则 |
| `CONTEXT.md` | 人+AI | 论文索引、当前活跃论文、进度 |
| `docs/` | 人+AI | 工作流说明、技能路由、维护规则 |
| `.claude/skills/paper-workflow/` | AI | 编排器 skill 本体 |

## 环境要求

| 组件 | 最低版本 | 说明 |
|------|:---:|------|
| Python | ≥3.10 | 脚本运行环境 |
| Pandoc | ≥3.0 | docx/tex 渲染引擎 |
| LaTeX (xelatex) | — | 可选。未安装时只生成 `.tex`，不编译 PDF |
| SVG 转换工具 | — | 可选。未安装时给出 warning，跳过转换 |

安装 Python 依赖：

```bash
pip install -r .claude/skills/paper-workflow/requirements.txt
```

探测当前环境：

```bash
python .claude/skills/paper-workflow/scripts/check_env.py
```

## 最小使用示例

```bash
# 1. 初始化一篇论文项目
python .claude/skills/paper-workflow/scripts/init_project.py ./my-paper \
  --slug my-paper --paper-type course_paper --language zh \
  --research-type review --discipline computer_science

# 2. 编写 manuscript/main.md（手动或用 nature-writing skill）
#    补充 literature/catalog.jsonl、references.bib 等文献文件

# 3. 查看项目状态
python .claude/skills/paper-workflow/scripts/commands.py status --project ./my-paper

# 4. 渲染输出
python .claude/skills/paper-workflow/scripts/render.py \
  --project ./my-paper --profile thesis-cn \
  --input manuscript/main.md --output-dir outputs

# 5. 质量核验
python .claude/skills/paper-workflow/scripts/qa_report.py \
  --project ./my-paper --output outputs/qa
```

## /paper-workflow 命令

在 Claude Code 中使用 `/paper-workflow` 前缀（需 `disable-model-invocation: true`，不会自动触发）：

| 命令 | 功能 |
|------|------|
| `/paper-workflow init` | 初始化论文项目 |
| `/paper-workflow status` | 查看阶段进度和产物 |
| `/paper-workflow resume` | 从断点恢复 |
| `/paper-workflow run <stage>` | 推进到指定阶段 |
| `/paper-workflow run <stage> --override` | 跳过依赖强制执行 |
| `/paper-workflow qa` | 运行质量核验 |
| `/paper-workflow render <profile>` | 输出终稿 |

## 渲染 Profile

| Profile | 输出 | 适用 |
|---------|------|------|
| `thesis-cn` | .docx | 中文学位论文 |
| `course-cn` | .docx | 中文课程论文 |
| `journal-word` | .docx | 英文期刊 Word |
| `journal-latex` | .tex | 英文期刊 LaTeX |
| `markdown-draft` | .md | 快速草稿 |

## 单篇论文项目目录结构

```
my-paper/
├── .paper-workflow/
│   ├── state.yaml              # 当前阶段与状态
│   ├── config.yaml             # 论文类型与配置
│   ├── artifact-manifest.jsonl # 产物追踪
│   └── search-log.jsonl        # 检索历史
├── manuscript/
│   └── main.md                 # 论文源稿
├── literature/
│   ├── catalog.jsonl           # 文献元数据库
│   ├── evidence-matrix.csv     # 文献→论据映射
│   ├── references.bib          # BibTeX 参考文献
│   └── references.csl.json     # CSL JSON 参考文献
├── citations/
│   └── claim-citation-map.csv  # 论点→引文映射
├── figures/
├── tables/
└── outputs/
    ├── thesis-cn-v001.docx
    ├── draft-v001.md
    ├── latest/                 # 仅通过 QA 后复制
    └── qa/                     # QA 报告
```

## MVP 功能范围

### 已支持

- 17 阶段状态机、依赖检查、断点恢复
- 文献库 CRUD（catalog.jsonl）、检索日志
- 5 级文献去重（DOI、标题、作者、来源关联、跨语言）
- 证据矩阵 + 论点引文映射
- BibTeX / CSL JSON 双格式导出
- 三轨渲染：docx / tex / md
- docx 幂等后处理
- 源稿 / 引文 / 输出 / 文献库四级校验
- 统一 QA 报告
- 283+ 测试覆盖

### 增强版（未实现）

- 系统综述完整流程
- 多 Subagent 并行阅读
- 复杂 Hook 自动化
- 完整数据分析适配器
- 批量 PDF 下载
- 大量学校/期刊模板
- 自动投稿

## 常见问题

**没有 LaTeX 能用吗？**
可以。`journal-latex` profile 会生成 `.tex` 文件，但不会编译 PDF。需要编译请安装 TeX Live 或 MiKTeX。

**没有 SVG 转换工具怎么办？**
渲染时给出 warning，SVG 图片不会被自动转换。安装 `pip install cairosvg` 或系统包 `librsvg` 即可。

**Word 输出为什么需要 Pandoc？**
Markdown → docx 转换由 Pandoc 完成，包括公式（OMML）、引用（citeproc）、目录生成。

**`[CITE NEEDED]` 怎么处理？**
写作阶段保留占位符，`citation_verification` 阶段统一补全。QA 报告会列出所有残留位置。

**`outputs/latest/` 是什么？**
每次渲染生成版本化文件（v001, v002...）。只有通过 QA 校验的版本才会复制到 `latest/`，方便直接取用最新终稿。

## 注意事项

- AI 生成内容需人工审核后投稿
- 引用必须通过检索工具验证，不能靠记忆
- 手稿、笔记、敏感研究内容注意隐私安全
- 学术判断由你来做，AI 负责辅助执行
