# Reference Docx 模板

此目录存放 Microsoft Word 参考文档（`.docx`），供 Pandoc `--reference-doc` 使用。

## 需要的文件

| 文件 | 用途 | Profile |
|------|------|---------|
| `thesis-cn-reference.docx` | 中文学位论文样式 | thesis-cn |
| `course-cn-reference.docx` | 中文课程论文样式 | course-cn |
| `journal-word-reference.docx` | 英文期刊 Word 样式 | journal-word |

## 创建 reference.docx

1. 用 Pandoc 生成默认模板：
   ```bash
   pandoc -o reference.docx --print-default-data-file reference.docx
   ```

2. 在 Word 中打开 `reference.docx`，修改样式：
   - 正文：宋体（中文）/ Times New Roman（英文），小四/12pt
   - 标题 1-3：黑体/加粗，适当字号
   - 页边距：按学校/期刊要求

3. 保存为对应的文件名，放入此目录

## 注意事项

- Pandoc 会继承 reference.docx 的样式定义（字体、字号、间距）
- `postprocess_docx.py` 只修复 Pandoc 已知 bug（MS Gothic → 宋体、三线表边框）
- 更多高级样式（页眉页脚、封面）建议在 Word 中手动调整
