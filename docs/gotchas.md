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

## paper-workflow

- [2026-06-15] **Windows GBK 终端 Unicode 崩溃**：print(\"✓\") 在 Windows Git Bash 中抛出 UnicodeEncodeError → scripts 中 print 只使用 ASCII（用 [OK]/[FAIL]/[WARN] 替代 Unicode 符号）。Markdown 报告文件（utf-8 写入）不受影响。
- [2026-06-15] **render.py 相对路径陷阱**：--input manuscript/main.md 相对于 cwd 而非 --project → 在 CLI 入口用 project_dir / args.input 解析。
- [2026-06-16] **内部 API 参数名不一致**：literature_store.py / search_logger.py 使用 `project_root`，但 evidence_manager.py / export_references.py / render.py 使用 `project_dir` → 全部统一为 `project_dir`，旧参数名保留为 deprecated alias。
- [2026-06-16] **commands.py 不支持 --project**：status / resume / run 要求用户 cd 到项目目录，但 render.py 和 qa_report.py 支持 --project → 所有 CLI 脚本统一支持 --project 参数，未传时自动向上查找 .paper-workflow/。
- [2026-06-16] **export_references.py 缺少友好的 --project 缺失提示**：未传 --project 且不在项目目录内时直接报 AttributeError → 所有 CLI 入口统一使用 _find_project_root() 自动发现，找不到时输出 "[ERROR] 未找到 .paper-workflow/ 目录"。
- [2026-06-16] **严禁编造文献**：不要"觉得应该引什么"就加什么。有参考 PDF → 先提取原文参考文献列表；无 PDF → 用 nature-academic-search / CrossRef API 搜索真实论文；每条 DOI 必须通过 CrossRef API 验证确认真实存在。违反 AGENTS.md 红线"不得编造论文内容、数据、引用、DOI"。
- [2026-06-16] **spec 中的分类表必须全文交叉核验**：v0.2 spec 初稿中 executor_type 数量统计表与各章节实际列出的阶段不一致（hybrid 声明 1 个但实际列出 2 个，script 声明 6 个但实际只有 4 个）→ spec 写作完成后必须对每张分类表做"数量 = 实例枚举"的双向校验。
- [2026-06-16] **skill_handoff 阶段的 done_conditions 必须拆两层**：literature_search 的 handoff 可以瞬间生成，但 catalog 新增记录需要用户实际执行搜索后才能完成 → skill_handoff 型阶段必须区分 `handoff_done`（handoff 文件已生成，进入 waiting_for_user）和 `stage_done`（用户完成 skill 执行后，产物满足完成条件）。不能混在一起，否则 `run` 会因为 catalog 还没记录直接 blocked。
- [2026-06-16] **spec-first 比 code-first 省时间**：v0.1.x 直接编码导致后期需要统一参数名、补齐 --project。v0.2 先写 spec → 用户审核发现 6 处设计问题 → 修正 spec → 再写 implementation plan。6 个设计问题如果到编码阶段才发现，至少要多改 5 个文件 + 重写测试。

---

## 待补充

> 以下场景在使用中积累：
> - 润色 skill 的失败边界
> - 图表 skill 的渲染失败
> - 跨 skill 路由误判
