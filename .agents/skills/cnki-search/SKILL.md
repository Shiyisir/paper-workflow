---
name: cnki-search
description: 当用户说"搜知网""找中文论文""查国内文献""在知网搜XX""搜一下知网"时加载。通过 Chrome 自动搜索 CNKI 并提取结构化结果列表。
argument-hint: "[搜索关键词]"
---

# CNKI 基础搜索

在知网按关键词搜索论文，返回结构化结果（标题、作者、期刊、日期、被引、下载）。

## 流程

1. **navigate** → `https://kns.cnki.net/kns8s/search`
2. **evaluate_script** → 执行 `scripts/search.js`（替换 `YOUR_KEYWORDS`）
3. **报告** → 按编号列表展示结果

## 工具调用: 2 (navigate + evaluate_script)

## 关键 Gotchas

- **不要 click 标题链接**：click 打开新 tab，浪费 3 个额外调用。用 `navigate_page` 直接访问 `href`。
- **搜索框需 dispatchEvent**：知网用 React，`input.value = query` 不触发 onChange → 必须 `dispatchEvent(new Event('input', { bubbles: true }))`。
- **验证码误判**：tcaptcha SDK 在 `top: -1000000px` 预载 DOM 是正常行为，只有 `top >= 0` 才是真验证码。详见 `../../references/cnki-captcha.md`。

## 不要导航到详情页

用户想看某篇论文时，用 `navigate_page` + 结果的 `href` 值，不要 click 链接。

## 附带文件

- `scripts/search.js` — 搜索 + 提取的 JS 代码
- `references/selectors.md` — 此 skill 的独有选择器
- `../../references/cnki-common-selectors.md` — 搜索结果页通用选择器
- `../../references/cnki-captcha.md` — 验证码检测逻辑
