---
name: cnki-advanced-search
description: 当用户说"高级检索""精确搜""按作者搜""限定期刊搜""只看北大核心/CSSCI/SCI/EI"时加载。通过知网旧版高级检索界面按多字段过滤。
argument-hint: "[用自然语言描述检索条件]"
---

# CNKI 高级检索

在知网**旧版**高级检索界面执行多字段过滤搜索（关键词、作者、期刊、日期范围、来源类别）。

## 为什么必须用旧版

新版界面（`kns8s/AdvSearch`）**没有来源类别复选框**（SCI/EI/北大核心/CSSCI 等）。旧版 URL 参数 `classid=7NS01R8M` 确保正确表单布局。

## 流程

1. **navigate** → `https://kns.cnki.net/kns/AdvSearch?classid=7NS01R8M`
2. **evaluate_script** → 执行 `scripts/search.js`，替换所有 `CONFIG` 占位符
3. **报告** → 展示过滤条件和结果数

## 解析参数

从 `$ARGUMENTS` 自然语言中提取：
- 主题关键词 / 篇名 / 关键词 → `query` + `fieldType`
- 作者 → `author`（字段 `#au_1_value1`）
- 期刊 → `journal`（字段 `#magazine_value1`）
- 日期范围 → `startYear` / `endYear`
- 来源类别 → `sourceTypes`（SCI/EI/hx=北大核心/CSSCI/CSCD）

## 工具调用: 2 (navigate + evaluate_script)

## 关键 Gotchas

- **必须用旧版 URL**：`kns.cnki.net/kns/AdvSearch`，不是 `kns8s/AdvSearch`。
- **来源类别互斥逻辑**：默认"全部期刊"勾选，选其他前必须先取消 `#gjAll`。
- **select 索引硬编码**：`selects[0]`=行1字段, `selects[5]`=行间逻辑, `selects[6]`=行2字段, `selects[14]`=起始年, `selects[15]`=结束年。索引随知网版本可能变动。

## 附带文件

- `scripts/search.js` — 高级检索函数
- `../../references/cnki-captcha.md` — 验证码检测逻辑
