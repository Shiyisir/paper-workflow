---
name: cnki-parse-results
description: 当用户已在知网搜索结果页时调用。解析当前页面结果，提取结构化论文数据。此 skill 不独立触发，由其他 skill 内部调用。
user-invokable: false
---

# CNKI 解析搜索结果

从当前知网搜索结果页提取结构化论文数据。

## 前置条件

当前 Chrome 页面必须是知网搜索结果页（URL 含 `kns.cnki.net`，页面含"条结果"）。

## 流程

1. **take_snapshot** → 确认在结果页（含"条结果"），检查验证码
2. **evaluate_script** → 执行 `scripts/parse.js`
3. **报告** → 按编号列表输出

## 降级方案

JS 提取失败时（DOM 结构变化），用 `take_snapshot` 手动解析 accessibility tree。

## 工具调用: 1 (evaluate_script) 或 2（含 snapshot 验证）

## 附带文件

- `scripts/parse.js` — 提取函数
- `../../references/cnki-common-selectors.md` — 搜索结果页选择器
