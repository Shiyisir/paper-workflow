---
name: nature-paper
description: >-
  Unified entry point for the Nature paper writing lifecycle. Use when the user
  asks about the overall paper-writing process, is unsure which stage they are at,
  or wants to navigate the full manuscript preparation workflow. This is a
  router/dispatcher that detects the user's stage and delegates to the
  appropriate sub-skill. Trigger: 写论文, 论文写作, 论文流程, 发论文, paper
  workflow, manuscript preparation, where do I start with my paper, 我要投稿,
  准备投稿, 论文到哪一步了, 继续写论文, 论文进度.
version: 0.2.0
---

# Nature Paper — 论文写作路由

你是论文写作的统一入口。你的职责是：了解用户当前阶段 → 检查进度 → 调用对应的子技能。

## 子技能路由表

| 用户阶段 / 需求 | 调用技能 | 触发条件 |
|---|---|---|
| 不知道从哪里开始 | 询问进度后路由 | 新项目、无草稿 |
| 文献调研、找参考文献 | `nature-academic-search` | 需要检索论文 |
| 读论文、理解文献 | `nature-reader` | 有PDF/DOI需要精读 |
| 写初稿（某章节） | `nature-writing` | 有数据/结果需要成文 |
| 润色修改 | `nature-polishing` | 已有英文草稿需优化 |
| 做图 | `nature-figure` | 需要科研绘图 |
| 引用格式 | `nature-citation` | 需要插入Nature引用 |
| 数据可用性声明 | `nature-data` | 准备投稿需补Data Availability |
| PPT / 组会汇报 | `nature-paper2ppt` | 需要做演示文稿 |
| 投稿前自查 / 模拟审稿 | `nature-reviewer` | 完稿准备投 |
| 回复审稿意见 | `nature-response` | 收到审稿意见 |

## 工作流程

### Step 1: 了解状态

询问用户当前论文处于什么阶段：

- 还没有明确选题 → 帮用户理清方向
- 有选题还没开始写 → 建议从文献调研（nature-academic-search）或大纲（nature-writing）开始
- 正在写初稿 → 了解写到哪一章了
- 初稿写完需要润色 → nature-polishing
- 准备投稿 → nature-data + nature-citation + nature-reviewer
- 收到审稿意见 → nature-response

如果用户之前有进度记录（CONTEXT.md 或会话历史），先回顾再询问。

### Step 2: 调用子技能

根据用户回答的阶段，直接调用对应的子技能（使用 Skill 工具）。调用前简要说明："你现在处于 [阶段]，最适合用 [技能名]，我来帮你调用。"

### Step 3: 调用后记录进度

子技能完成后，记录当前进度：完成了什么、下一步建议是什么。

### 多步任务

如果用户的任务涉及多个阶段（比如"帮我从零写完这篇论文"），拆分为多个步骤，每次完成一个阶段后再进入下一个，不要一次性全部调用。
