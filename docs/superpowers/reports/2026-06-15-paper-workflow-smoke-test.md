# paper-workflow Smoke Test 报告

> 日期：2026-06-15 | 版本：v0.1.0-mvp → v0.1.1 | 状态：通过

## 测试项目

| 项目 | 值 |
|------|-----|
| 路径 | `C:\Users\易朝亮\paper-smoke-test` |
| 论文 | 人工智能在喀斯特地区石漠化监测中的应用综述 |
| 类型 | 课程论文（course_paper） |
| 学科 | 交叉学科（interdisciplinary） |
| 语言 | 中文 |

## 测试数据规模

| 数据项 | 数量 |
|--------|:--:|
| 文献记录（catalog.jsonl） | 5 |
| 证据条目（evidence-matrix.csv） | 5 |
| 论点（claim-citation-map.csv） | 5 |
| 正文引用 citekey | 3 个（wang2024, zhang2023, li2022） |
| 图表 | 1 表 + 1 图 |

## 执行步骤与结果

| 步骤 | 命令 | 结果 |
|------|------|:--:|
| init | `init_project.py --slug ai-karst-monitoring ...` | ✅ |
| catalog 写入 | `literature_store.append_records()` | ✅ 5 条 |
| refs 导出 | `export_references.py --format both` | ✅ bib 5 + csl 5 |
| evidence | `evidence_manager.add_evidence_entry()` | ✅ 5 条 |
| claims | `evidence_manager.add_claim()` | ✅ 5 条，C001–C005 |
| catalog 校验 | `validate_catalog.py --project ...` | ✅ 0 errors |
| citations 校验 | `validate_citations.py --manuscript ...` | ⚠ 2 unused |
| render md | `render.py --profile markdown-draft` | ✅ draft-v001.md |
| render docx | `render.py --profile thesis-cn` | ✅ thesis-cn-v001.docx (12.2KB) |
| render tex | `render.py --profile journal-latex` | ✅ manuscript-v001.tex (3.7KB) |
| QA | `qa_report.py --project ...` | ⚠ passed_with_warnings |
| status | `commands.py status` | ✅ 正常 |
| resume | `commands.py resume` | ✅ 正常 |

## 输出文件

```
outputs/
├── draft-v001.md              # markdown-draft
├── thesis-cn-v001.docx        # thesis-cn (12.2 KB)
├── manuscript-v001.tex        # journal-latex (3.7 KB)
├── latest/
│   ├── draft.md
│   ├── thesis-cn.docx
│   └── manuscript.tex
└── qa/
    ├── qa-report-v001.md
    └── qa-report-v002.md
```

## QA 结果

- **总体状态**: `passed_with_warnings`
- **Errors**: 0
- **Warnings**: 2（bib 中有 2 条文献未在正文引用，符合设计预期）

## 发现的 Bug

### Bug 1：Windows GBK 终端 `print("✓")` 崩溃（中）

- **现象**: `init_project.py` 在 Windows Git Bash 下抛出 `UnicodeEncodeError: 'gbk' codec can't encode character '✓'`
- **根因**: Windows 终端默认 GBK 编码，Unicode checkmark 无法编码
- **修复**: 所有 CLI print 输出改用 ASCII 替代字符（`[OK]`/`[FAIL]`/`[WARN]`/`[BLOCKED]`）
- **影响范围**: `init_project.py`, `commands.py`, `fetch_csl.py`, `render.py`
- **修复 commit**: `23723cc`

### Bug 2：render.py 相对路径不解析 `--project`（高）

- **现象**: `render.py --project /path --input manuscript/main.md` 报"文件不存在"
- **根因**: CLI 中 `--input` 相对路径基于 cwd 解析，而非 `--project` 目录
- **修复**: `input_md = (project_dir / args.input).resolve()`
- **修复 commit**: `23723cc`

## 仍保留的 Warning（设计预期）

| Warning | 原因 | 是否需要处理 |
|---------|------|:--:|
| 2 条文献未在正文引用 | bib 中有但 manuscript 未 cite | 用户按需补引用即可 |
| 无 LaTeX 引擎 | 只生成 .tex 不编译 PDF | 安装 TeX Live 后可用 |
| 无 SVG 转换器 | SVG 图片跳过转换 | `pip install cairosvg` 后可用 |

## 是否建议进入 v0.2

**不建议。** 建议先用 1–2 个真实论文项目继续试用 v0.1.1，优先暴露引用核验、Word 后处理、中文路径等方面的问题。积累 gotchas 后再规划 v0.2。

当前 v0.1.1 已满足课程论文和简单投稿论文的 MVP 需求。
