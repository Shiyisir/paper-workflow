# paper-workflow 技能说明

论文写作编排器。通过 `/paper-workflow` 命令管理论文项目生命周期。

## 触发方式

- 命令前缀：`/paper-workflow init|status|resume|run|qa|render`
- `disable-model-invocation: true`：不会被自然语言自动触发
- 单次任务（如"搜知网""润色摘要"）由对应叶子 skill 自行触发

## 常用命令

所有命令支持 `--project` / `-p` 指定项目目录。未传时从当前目录向上查找 `.paper-workflow/` 自动发现。

```bash
# 项目初始化
python scripts/init_project.py <project_dir> --slug my-paper --paper-type course_paper --language zh

# 查看状态
python scripts/commands.py --project /path/to/project status [--verbose]
python scripts/commands.py status                         # 自动发现（需在项目目录内）

# 恢复中断
python scripts/commands.py --project /path/to/project resume

# 推进阶段
python scripts/commands.py --project /path/to/project run writing
python scripts/commands.py --project /path/to/project run literature_dedup --override

# 导出参考文献
python scripts/export_references.py --project /path/to/project --format both

# 渲染输出
python scripts/render.py --project /path/to/project --profile thesis-cn --input manuscript/main.md --output outputs/

# QA 核验
python scripts/qa_report.py --project /path/to/project

# 文献库校验
python scripts/validate_catalog.py --project /path/to/project
```

## 叶子 skill

| 能力 | 技能 |
|------|------|
| 英文文献搜索 | nature-academic-search |
| 中文文献搜索 | cnki-search |
| 深度阅读 | nature-reader |
| 撰写章节 | nature-writing |
| 图表制作 | nature-figure |
| 引文核验 | nature-citation |
| 语言润色 | nature-polishing |
| 投稿预审 | nature-reviewer |
| 审稿回复 | nature-response |
| 文献导出 | cnki-export |

## 脚本清单

| 脚本 | 职责 |
|------|------|
| `workflow_state.py` | 状态机引擎 |
| `init_project.py` | 项目初始化 |
| `literature_store.py` | 文献库 CRUD |
| `search_logger.py` | 检索历史 |
| `dedup.py` | 5 级去重 |
| `evidence_manager.py` | 证据矩阵与论点映射 |
| `export_references.py` | BibTeX/CSL JSON 导出 |
| `render.py` | 三轨渲染引擎 |
| `postprocess_docx.py` | Word 幂等后处理 |
| `qa_report.py` | 统一 QA 报告 |
| `validate_catalog.py` | 文献库校验 |
| `validate_citations.py` | 引文一致性校验 |
| `validate_manuscript.py` | 源稿结构校验 |
| `validate_docx.py` | docx 输出校验 |
| `validate_tex.py` | tex 输出校验 |
| `fetch_csl.py` | CSL 引用格式下载 |
| `check_env.py` | 环境探测 |
| `commands.py` | CLI 命令入口 |

## 测试

```bash
pytest .claude/skills/paper-workflow/tests/ -v
```

当前测试覆盖 M0–M7 所有脚本。
