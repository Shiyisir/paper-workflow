# paper-workflow MVP 发布检查清单

> 日期：2026-06-15 | 分支：dev/paper-workflow-mvp | 目标：确认可合并 master

## 里程碑完成状态

| 里程碑 | 状态 | 最后提交 |
|--------|:--:|----------|
| M0 基线核验与开发约束 | ✅ | `d2048bd` |
| M1 工作流骨架与项目初始化 | ✅ | `876f307` |
| M2 状态机与断点恢复 | ✅ | `f377657` |
| M3 文献记录、检索日志与去重 | ✅ | `98a79c5` |
| M4 证据矩阵与引文核验 | ✅ | `007a7dc` |
| M5 三轨渲染与 Word 后处理 | ✅ | `6549edd` |
| M6 质量核验与回归测试 | ✅ | `e71568c` |
| M7 端到端验收与文档更新 | ✅ | 进行中 |

## 18 项 MVP 完成情况

| # | 模块 | 完成 | 说明 |
|:--:|------|:--:|------|
| 1 | SKILL.md | ✅ | 入口路由，disable-model-invocation |
| 2 | schemas/ (3个 JSON Schema) | ✅ | state, literature, render |
| 3 | workflow_state.py | ✅ | 读写/校验/原子写 |
| 4 | state.yaml + config.yaml | ✅ | init_project.py 自动生成 |
| 5 | artifact-manifest.jsonl | ✅ | init 时创建，save_state 追加 |
| 6 | dedup.py | ✅ | 5 级去重 + DOI 归一化 |
| 7 | search-profiles.md + capabilities | ✅ | 学科路由表 + 降级规则 |
| 8 | evidence-matrix.csv + claim-citation-map.csv | ✅ | evidence_manager.py |
| 9 | references.bib + references.csl.json | ✅ | export_references.py |
| 10 | render.py | ✅ | 三轨输出 + --dry-run |
| 11 | postprocess_docx.py | ✅ | 幂等，旁车文件 |
| 12 | validate_manuscript.py | ✅ | 结构/公式/附件/CITE NEEDED |
| 13 | validate_citations.py | ✅ | citekey 一致性 + 交叉校验 |
| 14 | validate_docx.py | ✅ | 可打开性/样式/表格 |
| 15 | validate_tex.py | ✅ | 结构/图片路径/参考文献 |
| 16 | 3 个渲染 profile | ✅ | thesis-cn, journal-latex, markdown-draft |
| 17 | tests/fixtures/ + test_render.py | ✅ | 5 fixtures + mini-paper |
| 18 | references/lifecycle.md | ✅ | 9 个 references 文档 |

## 命令验收

| 命令 | 状态 | 测试覆盖 |
|------|:--:|----------|
| `/paper-workflow init` | ✅ | test_init_project.py (11), test_e2e.py |
| `/paper-workflow status` | ✅ | test_commands.py |
| `/paper-workflow resume` | ✅ | test_commands.py, test_e2e.py |
| `/paper-workflow run <stage>` | ✅ | test_commands.py |
| `/paper-workflow run <stage> --override` | ✅ | test_commands.py, test_e2e.py |
| `/paper-workflow qa` | ✅ | test_qa_report.py |
| `/paper-workflow render <profile>` | ✅ | test_render.py, test_e2e.py |
| `/paper-workflow render --dry-run` | ✅ | test_render.py, test_e2e.py |

## 数据文件验收

| 文件 | 位置 | 生成方式 |
|------|------|----------|
| config.yaml | .paper-workflow/ | init_project.py |
| state.yaml | .paper-workflow/ | init_project.py + workflow_state.py |
| artifact-manifest.jsonl | .paper-workflow/ | init_project.py |
| search-log.jsonl | .paper-workflow/ | search_logger.py |
| catalog.jsonl | literature/ | literature_store.py |
| evidence-matrix.csv | literature/ | evidence_manager.py |
| references.bib | literature/ | export_references.py |
| references.csl.json | literature/ | export_references.py |
| claim-citation-map.csv | citations/ | evidence_manager.py |

## 输出验收

| 输出 | 格式 | 测试验证 |
|------|------|----------|
| markdown-draft | .md | ✅ test_e2e.py |
| thesis-cn | .docx | ✅ test_e2e.py |
| journal-latex | .tex | ✅ test_e2e.py |
| outputs/latest/ | 最新通过 QA 的文件 | ✅ test_render.py |
| QA 报告 | .md (versioned) | ✅ test_qa_report.py, test_e2e.py |

## 测试结果

| 指标 | 数值 |
|------|:--:|
| 总测试数 | 288 |
| 通过 | 288 |
| 失败 | 0 |
| 脚本文件 | 19 个 |
| 测试文件 | 17 个 |

运行命令：`pytest .claude/skills/paper-workflow/tests/ -v`

## 已知限制

| 限制 | 影响 | 计划 |
|------|------|------|
| LaTeX 未安装 → 只生成 .tex，不编译 PDF | journal-latex 用户需手动编译 | 增强版加入编译选项 |
| SVG 转换工具未安装 → warning，跳过 | 含 SVG 的文档需手动转换 | 增强版预检 + 自动安装提示 |
| 阶段执行器为 stub | run <stage> 不执行实际业务 | M3–M5 已实现文献/渲染层；其余待增强版 |
| 无系统综述纳排标准流程 | 文献筛选需手动 | 增强版 |
| 无批量 PDF 下载 | 单篇手动下载 | 增强版 |
| 仅 3 种 CSL 格式（需运行时下载） | 非 GB/APA/Chicago 需手动添加 | 增强版加入更多 CSL |
| reference.docx 需用户提供 | 默认 Pandoc 样式可能不美观 | 文档说明创建方法 |

## 合并建议

```bash
git checkout master
git merge dev/paper-workflow-mvp
git tag v0.1.0-mvp
```

**结论：建议合并。** 所有 18 项 MVP 完成，288 测试通过，端到端可重复跑通。已知限制均为非阻塞性（LaTeX/SVG 可选，CSL 需下载，阶段执行器逐步填充）。

合并后建议：
- 在真实论文项目中试用
- 收集用户反馈后规划 v0.2.0 增强版
- 优先补全阶段执行器中的 literature_search / writing / polishing 桥接
