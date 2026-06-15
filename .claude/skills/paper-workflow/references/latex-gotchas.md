# LaTeX 避坑规则（按 profile 分层）

## 全局规则（所有 profile）

### 1. 禁用 `\tag{}`（docx-safe profile）
**问题**：Pandoc 转换 `\tag{1}` 到 OMML 时会报"未知控制序列"错误。
**正确做法**：使用 Pandoc 原生公式编号语法或手动编号。

### 2. 禁止 Unicode 下标
**问题**：`n₁`（Unicode 下标 1）在 Arial 字体会显示为缺字方块。
**正确做法**：使用 `$n_1$`（LaTeX 数学模式）。

```markdown
<!-- 错误 -->
n₁ + n₂ = n₃

<!-- 正确 -->
$n_1 + n_2 = n_3$
```

### 3. `\newline` 不在标题中使用
**问题**：Pandoc 在标题中遇到 `\newline` 导致解析错误。
**正确做法**：标题只用纯文本，换行用 Pandoc 的 `\` 行末反斜杠。

### 4. YAML frontmatter 避免误生成标题页
**问题**：Pandoc 默认将 Markdown frontmatter 渲染为标题页，可能与 `reference.docx` 或 LaTeX 模板冲突。
**正确做法**：使用独立 `metadata.yaml` 文件（`--metadata-file`），不在 manuscript/main.md 开头写 YAML frontmatter。

### 5. `--number-sections` 按 profile 开关
| Profile | 开关 | 原因 |
|---------|:---:|------|
| thesis-cn | 关 | 中文论文通常手动编号 |
| course-cn | 关 | 同上 |
| journal-word | 开 | 英文期刊通用 |
| journal-latex | 开 | LaTeX 模板通常自动编号 |

## docx-safe profile 专项

### 6. 公式字体
Pandoc → OMML 默认使用 Latin Modern Math，在 Windows Word 中可能不兼容。
**缓解**：确保 reference.docx 已预设公式字体为 Cambria Math。

### 7. 表格
Pandoc 生成的 docx 表默认无边框。
**缓解**：`postprocess_docx.py` 自动添加三线表样式。

### 8. 中文字体
Pandoc 可能将中文段落设为 MS Gothic。
**缓解**：`postprocess_docx.py` 检测并替换为宋体。

### 9. 图表编号
Pandoc 不自动编号。图片说明中的"图1""图2"由作者手动编号。
**缓解**：`validate_manuscript.py` 检测编号连续性。

## journal-latex profile 专项

### 10. 图片路径
LaTeX 编译时的图片路径相对于 .tex 文件位置，不是 Markdown 源文件位置。
**缓解**：`render.py` 自动调整 `\includegraphics` 路径。

### 11. 编码
中文 LaTeX 需要 `xeCJK` 包或使用 `xelatex` 编译。
**缓解**：LaTeX 模板预置编码配置。

### 12. 引用格式
BibLaTeX vs natbib：Pandoc 默认使用 `--biblatex` 或 `--natbib` 生成引用命令。
**缓解**：根据模板选择对应参数。

## 渲染失败时的排查顺序

1. Pandoc 版本 ≥3.0（`pandoc --version`）
2. `--citeproc` 过滤器可用（`pandoc --citeproc --version`）
3. CSL 文件存在且格式正确
4. reference.docx 存在（docx profile）
5. LaTeX 模板存在且可编译（tex profile）
6. metadata.yaml 格式正确
7. 源稿 Markdown 语法正确
