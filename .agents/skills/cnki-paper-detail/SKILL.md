---
name: cnki-paper-detail
description: 当用户说"看摘要""论文详情""这篇论文讲了什么""提取关键词""查引用"时加载。从知网论文详情页提取完整元数据。
argument-hint: "[论文 URL 或留空（已在详情页）]"
---

# CNKI 论文详情提取

从知网论文详情页提取标题、作者、机构、摘要、关键词、基金、分类号、引用网络等完整元数据。

## 流程

1. **navigate_page** → 论文详情 URL（如提供）或 `wait_for` "摘要"
2. **take_snapshot** → 检查验证码
3. **evaluate_script** → 执行 `scripts/extract.js`
4. **格式化输出** → 结构化展示所有字段
5. **降级方案** → JS 提取失败时，用 snapshot 手动解析 accessibility tree

## 提取字段

标题、作者（含机构编号）、机构、摘要、关键词、基金、分类号、期刊、出版信息、是否网络首发、文章目录、引用网络统计。

## 降级解析（snapshot）

| 数据 | 定位方式 |
|------|----------|
| 标题 | `heading` level 1 |
| 作者 | `link` URL 含 `kcms2/author/detail` |
| 机构 | `link` URL 含 `kcms2/organ/detail` |
| 摘要 | `StaticText` 在"摘要："之后 |
| 关键词 | `link` URL 含 `kcms2/keyword/detail` |
| 基金 | `link` 在"基金资助："之后 |
| 分类号 | `StaticText` 在"分类号："之后 |

## 附带文件

- `scripts/extract.js` — 提取函数
- `../../references/cnki-common-selectors.md` — 详情页选择器
