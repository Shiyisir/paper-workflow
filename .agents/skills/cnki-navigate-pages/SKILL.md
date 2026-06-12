---
name: cnki-navigate-pages
description: 当用户在知网搜索结果中说"下一页""上一页""翻到第N页""按时间排序""按被引排序""按下载排序"时加载。通过单次 evaluate_script 完成翻页或排序。
argument-hint: "[next|previous|page N|sort by date|citations|downloads|relevance|comprehensive]"
---

# CNKI 翻页与排序

在知网搜索结果页上翻页或切换排序方式。所有操作均用单次 `evaluate_script`。

## 流程

### 翻页

执行 `scripts/navigate.js` 翻页函数，替换 `ACTION_HERE` 为 `"next"` / `"previous"` / `"page 3"`。

### 排序

执行 `scripts/navigate.js` 排序函数，替换 `SORT_HERE` 为：
- `relevance`（相关度）
- `date`（发表时间）
- `citations`（被引）
- `downloads`（下载）
- `comprehensive`（综合）

## 工具调用: 1 (evaluate_script)

## 关键 Gotchas

- 翻页/排序后页面重置，先前提取的结果作废。
- 等待策略：检测 `.countPageMark` 变化确认页面已刷新，不要用固定 `setTimeout`。
- 验证码见 `../../references/cnki-captcha.md`。

## 附带文件

- `scripts/navigate.js` — 翻页 + 排序函数
- `../../references/cnki-common-selectors.md` — 翻页/排序选择器
