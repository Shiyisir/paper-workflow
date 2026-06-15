# paper-workflow 技能说明

论文写作编排器。通过 `/paper-workflow` 命令管理论文项目生命周期。

## 触发方式

- 命令前缀：`/paper-workflow init|status|resume|run|qa|render`
- `disable-model-invocation: true`：不会被自然语言自动触发
- 单次任务（如"搜知网""润色摘要"）由对应叶子 skill 自行触发

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

当前 288 个测试覆盖 M0–M7 所有脚本。
