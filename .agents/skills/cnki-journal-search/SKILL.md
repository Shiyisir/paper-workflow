---
name: cnki-journal-search
description: 当用户说"搜期刊""查期刊""XX期刊的影响因子""找XX学报"时加载。通过知网期刊导航按刊名/ISSN/CN 搜索期刊。
argument-hint: "[期刊名 或 ISSN 或 CN号]"
---

# CNKI 期刊检索

在知网期刊导航中搜索期刊，返回刊名、ISSN、影响因子、被引/下载等。

## 流程

1. **navigate** → `https://navi.cnki.net/knavi`
2. **evaluate_script** → 执行 `scripts/search.js`（替换 `QUERY_HERE`）
3. **报告** → 按编号列表展示期刊结果

## 自动识别搜索类型

脚本自动按格式判断：
- `/^\d{4}-\d{3}[\dXx]$/` → ISSN 搜索
- `/^\d{2}-\d{4}/` → CN 搜索
- 其他 → 刊名搜索

## 工具调用: 2 (navigate + evaluate_script)

## 关键 Gotchas

- **期刊详情页开新 tab**：点击期刊链接后需 `list_pages` + `select_page` 切换。
- **仅 1 条结果时**可自动跳转详情，调用 `cnki-journal-index`。
- **搜索按钮选择器**：`input.researchbtn`，不是通用 `button`。

## 附带文件

- `scripts/search.js` — 搜索 + 提取函数
