# cnki-search 选择器

此 skill 独有的选择器（通用选择器见 `../../references/cnki-common-selectors.md`）。

## 结果行提取字段（搜索结果页）

| 数据 | 提取方式 |
|------|----------|
| 序号 | `i + 1`（0-indexed） |
| 标题 | `td.name a.fz14` → `innerText.trim()` |
| 链接 | `td.name a.fz14` → `href` |
| Export ID | `input.cbItem[i]` → `value` |
| 作者列表 | `td.author a.KnowledgeNetLink` 遍历 → `innerText.trim()` |
| 期刊 | `td.source a` → `innerText.trim()` |
| 日期 | `td.date` → `innerText.trim()` |
| 被引 | `td.quote` → `innerText.trim()` |
| 下载 | `td.download` → `innerText.trim()` |

## Gotchas

- **不要 click 标题链接**：click 会在新 tab 打开，浪费 3 个额外 tool call（list_pages + select_page + take_snapshot）。用 `navigate_page` 直接打开 `href` 值。
- **搜索输入框需 dispatchEvent**：CNKI 用 React，单纯 `input.value = query` 不会触发 onChange，必须 `dispatchEvent(new Event('input', { bubbles: true }))`。
- **等待策略**：等 `.search-input` 出现 → 等 "条结果" 文本出现，不要用固定 `setTimeout`。
