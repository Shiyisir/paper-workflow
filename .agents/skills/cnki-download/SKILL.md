---
name: cnki-download
description: 当用户说"下载这篇论文""下PDF""下载CAJ""帮我下载知网论文"时加载。需用户已登录知网。通过 Chrome 触发 PDF/CAJ 下载。
argument-hint: "[论文 URL 或留空（已在详情页）]"
---

# CNKI 文献下载

从知网论文详情页触发 PDF 或 CAJ 下载。

## 前置条件

用户**必须已登录**知网账号且有下载权限。

## 流程

1. **navigate_page** → 论文详情 URL（如提供），否则用当前页面
2. **evaluate_script** → 执行 `scripts/download.js`（替换 `FORMAT` 为 `"pdf"` 或 `"caj"`）
3. **报告结果**：
   - `status: downloading` → "PDF 下载已触发：{title}。请在 Chrome 下载管理器中查看。"
   - `error: not_logged_in` → 提示登录
   - `error: captcha` → 提示手动验证

## 工具调用: 1–2 (navigate + evaluate_script)

## 关键 Gotchas

- **不要 click 标题链接**：click 打开新 tab，浪费 3 个调用。用 `navigate_page` 直接访问 URL。
- **登录态检查**：`.downloadlink.icon-notlogged` 存在 = 未登录。
- **PDF 优先**：有 PDF 则优先 PDF，否则降级 CAJ。

## 附带文件

- `scripts/download.js` — 下载检测与触发函数
- `../../references/cnki-captcha.md` — 验证码检测逻辑
