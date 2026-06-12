---
name: cnki-journal-toc
description: 当用户说"看目录""浏览期刊""XX期刊第X期""下载原版目录""封面目录"时加载。浏览知网期刊某一期的论文列表或下载原版目录 PDF。
argument-hint: "[期刊名] [年份] [期号] [download]"
---

# CNKI 期刊目录浏览

浏览指定期刊某一期的论文列表，可选下载原版目录 PDF（封面+目录扫描）。

## 流程

### 浏览目录

1. 确保在期刊详情页（否则先调用 `cnki-journal-search`）
2. **evaluate_script** → 执行 `scripts/browse.js`（替换 `YEAR` / `ISSUE`）
3. **报告** → 按编号列出该期论文

### 下载原版目录 PDF

1. 找到"原版目录浏览"链接（`a.btn-preview:not(.btn-back)`）
2. click → 新 tab 打开阅读器
3. `list_pages` → `select_page` → 找"下载"按钮 → click

## 关键 Gotchas

- **"原版目录浏览"仅在选中具体期后出现**，网络首发视图无此选项。
- **阅读器开新 tab** → 需 tab 切换，不能直接 `navigate_page`。
- **下载需要登录**，下载 URL 是 session 绑定的，不可缓存。

## 附带文件

- `scripts/browse.js` — 选期 + 提取论文列表
- `../../references/cnki-common-selectors.md` — 期刊目录页选择器
