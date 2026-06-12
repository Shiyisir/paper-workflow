# Gotchas & 踩坑日志

> 从真实失败中总结出来的"别这么做"清单。每条必须注明日期和来源，排序按模块。

## 记录规则

- 每次任务发现新的失败模式 → 立即追加
- 格式：`[日期] 问题 → 根因 → 正确做法`
- 定期检查：5 条同类问题时考虑加进对应 skill 的 SKILL.md gotchas 节

---

## CNKI 通用

- [2026-06-12] **验证码误判**：tcaptcha SDK 在 `top: -1000000px` 预加载 DOM 是正常的，只有 `top >= 0` 才是真验证码 → 始终检查 `getBoundingClientRect().top >= 0`
- [2026-06-12] **搜索结果不更新**：知网用 React，`input.value = query` 不触发事件 → 必须 `dispatchEvent(new Event('input', { bubbles: true }))`
- [2026-06-12] **频繁操作触发验证码**：约 5-8 次请求后知网开始限流 → 合并调用，避免不必要的独立请求

## CNKI 搜索

- [2026-06-12] **click 标题浪费 3 个 tool call**：click 打开新 tab → 需 list_pages + select_page + take_snapshot → 用 `navigate_page` 直接访问 `href`

## CNKI 高级检索

- [2026-06-12] **新版无来源类别复选框**：必须用旧版 URL（`kns.cnki.net/kns/AdvSearch`），不是 `kns8s/AdvSearch`
- [2026-06-12] **select 索引硬编码**：`selects[0]`=行1字段, `selects[5]`=行间逻辑, `selects[14]`=起始年 → 索引随知网版本可能变动

## CNKI 导出

- [2026-06-12] **Windows 编码问题**：bash/curl 直接传中文 JSON 会乱码 → 必须用 Python 脚本处理
- [2026-06-12] **批量导出省 90% 调用**：9 篇论文逐一导出 = 33 次调用，批量 = 3 次 → 始终优先使用 `scripts/batch-export.js`

## 期刊查询

- [2026-06-12] **"更多介绍"需要手动 click**：默认不展开详细收录年份 → 提取完后检查 `hasMoreIntro`
- [2026-06-12] **期刊详情开新 tab**：从期刊搜索跳转时默认新 tab → 需 `list_pages` + `select_page`

## 文献下载

- [2026-06-12] **下载必须登录**：未登录时 `.downloadlink.icon-notlogged` 存在 → 先检测再下载

---

## 待补充

> 以下场景在使用中积累：
> - 润色 skill 的失败边界
> - 图表 skill 的渲染失败
> - 跨 skill 路由误判
