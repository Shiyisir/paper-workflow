# Pandoc 渲染流程与命令模板

## 渲染链

`render.py` 内部执行顺序：

```
1. validate_manuscript.py     ← 检查源稿结构/公式/图片/[CITE NEEDED]
2. pandoc + citeproc          ← 核心转换（Markdown → docx/tex/md）
3. SVG 转换                   ← SVG → PNG（docx profile）/ PDF（tex profile）
4. postprocess_docx.py        ← Word 后处理（仅 docx profile，幂等）
5. validate_docx.py / validate_tex.py ← 输出文件校验
6. QA 报告输出
```

## 渲染 profile 配置项

```yaml
output: docx                  # docx | tex | md
reference_doc: templates/docx/thesis-cn-reference.docx  # 仅 docx
csl: templates/csl/gb-t-7714.csl
metadata: null                # metadata.yaml 路径（可选，避免 YAML frontmatter 误生成标题页）
number_sections: false        # 章节编号（中文通常关）
native_math: omml             # omml | latex | raw
convert_svg_to: png           # png | pdf | none
toc: true                     # 是否生成目录
toc_depth: 3                  # 目录深度
caption_style: chinese        # chinese | english
postprocess: true             # 是否运行 postprocess_docx.py
latex_template: null          # 仅 tex profile
```

## Pandoc 命令模板

### docx-safe（中文论文）

```bash
pandoc manuscript/main.md \
  --from markdown+smart \
  --to docx \
  --output outputs/thesis-v001.docx \
  --reference-doc templates/docx/thesis-cn-reference.docx \
  --metadata-file metadata.yaml \
  --csl templates/csl/gb-t-7714.csl \
  --citeproc \
  --toc --toc-depth=3 \
  --number-sections \
  --wrap=preserve
```

### journal-latex（英文投稿）

```bash
pandoc manuscript/main.md \
  --from markdown+smart \
  --to latex \
  --output outputs/manuscript-v001.tex \
  --template templates/latex/journal.tex \
  --metadata-file metadata.yaml \
  --csl templates/csl/apa.csl \
  --citeproc \
  --number-sections \
  --wrap=preserve
```

### markdown-draft（快速草稿）

```bash
pandoc manuscript/main.md \
  --from markdown+smart \
  --to markdown-smart \
  --output outputs/draft-v001.md \
  --wrap=preserve
```

## metadata.yaml 示例

```yaml
title: "论文标题"
author: "作者姓名"
date: "2026-06-12"
institute: "机构名称"
abstract: "摘要内容"
keywords: ["关键词1", "关键词2"]
bibliography: "literature/references.bib"
```

## 版本化输出

```
outputs/
├── thesis-v001.docx    ← 第一次渲染
├── thesis-v002.docx    ← 修改后重新渲染
├── thesis-v003.docx    ← 最新版本
├── latest/
│   └── thesis.docx     ← 仅通过 QA 后复制
└── qa/
    ├── thesis-v003-validation.md
    ├── thesis-v003-citations.md
    └── originality-self-audit.md
```

版本号规则：扫描 outputs/ 目录，找到最大版本号 → +1。首次为 v001。

## 错误处理

| 错误 | 处理 |
|------|------|
| Pandoc 命令失败（非零返回） | 渲染中断，不继续后处理，报告错误输出 |
| 源稿校验失败 | 渲染中断，报告校验错误 |
| SVG 转换工具不可用 | 记录 warning，跳过转换 |
| citeproc 引用错误 | Pandoc 输出 [???] 占位符 → validate_citations 检测到 |
