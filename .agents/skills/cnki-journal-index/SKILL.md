---
name: cnki-journal-index
description: 当用户说"这个期刊什么级别""是不是核心""查收录""影响因子多少""被哪些数据库收录"时加载。通过知网期刊详情页查询收录状态和评价指标。
argument-hint: "[期刊名 或 期刊详情URL]"
---

# CNKI 期刊收录查询

查询期刊在知网的收录状态（北大核心/CSSCI/CSCD/SCI/EI 等）、影响因子和基本信息。

## 流程

1. **导航到期刊详情页**（提供刊名则先搜索，提供 URL 则直接跳转）
2. **take_snapshot** → 检查验证码
3. **evaluate_script** → 执行 `scripts/extract.js`
4. **可选**：如有"更多介绍"链接 → click 展开 → 重新 snapshot
5. **报告** → 格式化输出收录状态 + 评价指标

## 报告格式

```
## {nameCN} ({nameEN})

**收录：** {indexedIn}
**基本信息：** ISSN/CN/主办/周期
**评价：** 复合影响因子 / 综合影响因子
```

## 关键 Gotchas

- **详情页开新 tab**：从期刊搜索跳转时需处理 tab 切换。
- **"更多介绍"需要手动 click**：默认不展开详细收录年份信息。
- **影响因子年份**：知网显示为"复合影响因子(2025版)"，非实时数据。

## 附带文件

- `scripts/extract.js` — 提取函数
- `../../references/cnki-common-selectors.md` — 期刊详情页选择器
