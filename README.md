# 论文工作流

一个学术写作工作台：用 AI skills 辅助完成“检索 → 阅读 → 写作 → 图表 → 润色 → 投稿回复 → 汇报”。

本项目不是传统代码项目，核心资产是：
- 工作流规则
- 论文模板
- 多篇论文的进度管理

## 这个项目怎么理解

- README.md：给人看，项目入口
- AGENTS.md：给 AI 看，行为规则
- CONTEXT.md：运行时状态，论文索引和当前进度
- docs/：维护文档，详细说明放这里
- _template/：新论文的固定骨架

## 目录结构

`	ext
论文工作流/
├─ README.md
├─ AGENTS.md
├─ CONTEXT.md
├─ _template/
│  ├─ README.md
│  ├─ CONTEXT.md
│  ├─ manuscript/
│  ├─ notes/
│  ├─ references/
│  ├─ figures/
│  └─ outputs/
├─ docs/
│  ├─ workflow.md
│  ├─ skills-routing.md
│  ├─ setup.md
│  └─ maintenance.md
├─ <paper-slug>/
├─ .codex/
│  ├─ config.toml
│  └─ agents/
├─ .agents/
│  └─ cnki-researcher.md
└─ CHANGELOG.md
`

## 快速开始

### 1. 开一篇新论文
说：

- 开始写新论文

AI 会：
1. 确定论文简称
2. 从 _template/ 复制出新论文文件夹
3. 填写论文 CONTEXT.md
4. 更新根 CONTEXT.md

### 2. 切换论文
说：

- 切换到 XX 论文

### 3. 查看当前该做什么
先读：
- 根 CONTEXT.md
- 当前活跃论文的 CONTEXT.md

## 常用入口

| 你想做什么 | 去哪里看 |
|---|---|
| 项目总览 | README.md |
| AI 执行规则 | AGENTS.md |
| 论文索引与进度 | CONTEXT.md |
| 工作流说明 | docs/workflow.md |
| 技能路由说明 | docs/skills-routing.md |
| 环境准备 | docs/setup.md |
| 文档维护规则 | docs/maintenance.md |

## 注意事项

- AI 生成内容需人工审核后才能投稿
- 手稿、笔记、敏感研究内容注意隐私安全
- 引用必须通过检索工具验证，不能靠记忆
- 学术判断由你来做，AI 负责辅助执行
