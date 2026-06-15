# 技能路由说明

本文档用于指导 AI 在不同请求下选择正确的 skill。

## 总原则

- `/paper-workflow ...` 命令 → paper-workflow 编排器（项目模式）
- 自然语言 → 叶子 skill 直接响应（单次任务模式）
- 用户需求模糊时，先判断阶段，再建议技能
- 知网相关操作前，先检查 Chrome 是否可达
- 英文主题优先国际文献；中文主题分情况判断来源

## 编排路由（paper-workflow）

| 命令 | 功能 |
|------|------|
| `/paper-workflow init` | 初始化论文项目 |
| `/paper-workflow status` | 查看阶段进度 |
| `/paper-workflow resume` | 从断点恢复 |
| `/paper-workflow run <stage>` | 推进阶段 |
| `/paper-workflow qa` | 运行质量核验 |
| `/paper-workflow render <profile>` | 输出终稿 |

## 通用路由

| 用户请求 | 优先技能 | 说明 |
|---|---|---|
| 搜英文/国际论文 | nature-academic-search | PubMed/CrossRef/arXiv |
| 搜中文论文 | cnki-search 或 cnki-researcher | 需要 Chrome |
| 查期刊级别/核心/影响因子 | cnki-journal-index | |
| 下载论文 PDF/CAJ | cnki-download | 需要知网登录 |
| 导出到 Zotero | cnki-export zotero | |
| 读论文/翻译/做阅读笔记 | nature-reader | |
| 起草论文章节 | nature-writing | |
| 润色学术英语 | nature-polishing | |
| 为段落补引文 | nature-citation | |
| 做论文图表 | nature-figure | 先确认 Python/R |
| 写 Data Availability | nature-data | |
| 回复审稿意见 | nature-response | |
| 论文转 PPT | nature-paper2ppt | |
| 不确定该用什么 | nature-paper 入口 | 自动阶段判断 |

## 检索源判断

### 直接走国际文献
- 英文关键词
- 国际前沿主题
- 用户明确要求英文文献

### 直接走 CNKI
- 明显中国特色主题
- 中文政策、中文期刊、国内研究问题
- 用户明确要求中文论文

### 先问用户
- 未指定语言
- 中外都可能相关
- 不确定目标读者是国际还是国内

## 知网前置自检

执行 CNKI 技能前：
1. 检查 Chrome 是否可达
2. 可达 → 继续
3. 不可达 → 提示用户启动 Chrome

## 降级方案

Chrome 不可用时：
- 国际主题 → 建议国际文献源
- 中文独家内容 → 建议用户手动访问知网
- 不卡死，不反复重试

## Eval 用例

> 每次发现路由错误时追加新用例。至少每周跑一次核心用例。

### 检索路由

| # | 用户输入 | 期望路由 | 备注 |
|---|----------|----------|------|
| 1 | "搜知网储能论文" | cnki-search | 明确知网 + 中文主题 |
| 2 | "search PubMed for perovskite solar cells" | nature-academic-search | 英文 + 指定数据库 |
| 3 | "帮我找一下钙钛矿论文" | 先问（中外） | 未指定来源，歧义 |
| 4 | "在知网用高级检索，搜2020-2025的北大核心储能论文" | cnki-advanced-search | 多条件过滤 |
| 5 | "把刚才搜到的论文导出到Zotero" | cnki-export | 已搜 + 导出意图 |

### 期刊路由

| # | 用户输入 | 期望路由 | 备注 |
|---|----------|----------|------|
| 6 | "计算机学报是什么级别的" | cnki-journal-index | 收录查询 |
| 7 | "搜一下计算机学报这个期刊" | cnki-journal-search | 期刊检索 |
| 8 | "看看计算机学报2026年第1期有什么论文" | cnki-journal-toc | 目录浏览 |

### 论文详情路由

| # | 用户输入 | 期望路由 | 备注 |
|---|----------|----------|------|
| 9 | "这篇论文讲了什么" | cnki-paper-detail | 在详情页 |
| 10 | "下载这篇论文的PDF" | cnki-download | 在详情页 |

### 翻页排序路由

| # | 用户输入 | 期望路由 | 备注 |
|---|----------|----------|------|
| 11 | "下一页" | cnki-navigate-pages | 在结果页 |
| 12 | "按被引排序" | cnki-navigate-pages | 排序 |

### 边界测试

| # | 用户输入 | 预期行为 | 备注 |
|---|----------|----------|------|
| 13 | "帮我写论文" | nature-paper 入口 | 阶段判断 |
| 14 | "润色这段英文摘要" | nature-polishing | 明确润色 |
| 15 | "把这篇论文做成PPT" | nature-paper2ppt | 论文转演示 |
| 16 | "搜知网"（Chrome 未启动） | 提示用户启动 Chrome | 前置自检 |

