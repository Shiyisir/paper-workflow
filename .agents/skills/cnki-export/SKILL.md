---
name: cnki-export
description: 当用户说"导出到Zotero""导出引用""保存到文献管理""导出RIS""GB/T引用""批量导出"时加载。从知网导出论文元数据，推送到 Zotero 或保存为文件。
argument-hint: "[zotero|ris|gb] [论文URL 或留空（已在详情页）]"
---

# CNKI 导出 & Zotero 集成

从知网导出论文引用数据：推送到 Zotero 桌面端、保存 RIS 文件、或输出 GB/T 7714 引用文本。

## 参数

- `zotero`（默认）— 推送到 Zotero 桌面端
- `ris` — 保存为 `.ris` 文件
- `gb` — 输出 GB/T 7714 引用文本
- 可选附带论文 URL

## 模式选择

| 场景 | 模式 | Tool call 数 |
|------|------|-------------|
| 在论文详情页 | 单篇导出 | 1 evaluate + 1 bash = 2 |
| 在搜索结果页，导出全部/部分 | **批量导出（优先）** | 1 evaluate + 1 bash = 2 |
| 需搜索后导出 | 先 cnki-search，再批量 | 4 总计 |

## 流程

### 单篇导出（从详情页）

1. **evaluate_script** → 执行 `scripts/single-export.js`
2. **bash** → `python "scripts/push_to_zotero.py" /tmp/papers.json`

### 批量导出（从搜索结果页，优先）

1. **evaluate_script** → 执行 `scripts/batch-export.js`
   - 全部导出：用默认 for 循环
   - 部分导出：替换为 `indices` 数组过滤
2. **bash** → `python "scripts/push_to_zotero.py" /tmp/papers.json`

## 报告

```
已添加到 Zotero: {title}
  作者: {authors}
  期刊: {journal}
GB/T 7714: {gbt_citation}
```

批量时：`已批量添加 {count} 篇论文到 Zotero`

## 关键 Gotchas

- **Windows 编码**：不能通过 bash/curl 直接传中文 JSON，必须用 Python 脚本处理。
- **Zotero 必须运行**：`localhost:23119` 仅在 Zotero 桌面端运行时可用。
- **中文作者**：用 `name` 字段（单字段），`creatorType: "author"`。
- **批量导出省 90% tool call**：9 篇论文从 33 次调用降到 3 次。
- **导出 API 的 filename 必须是加密 ID**（`#export-id` 或 `input.cbItem` value），不是 `#paramfilename`。

## 附带文件

- `scripts/single-export.js` — 单篇导出函数
- `scripts/batch-export.js` — 批量导出函数
- `references/api.md` — 导出 API 和 Zotero API 参考
- `../../references/cnki-common-selectors.md` — 搜索结果页/详情页选择器
