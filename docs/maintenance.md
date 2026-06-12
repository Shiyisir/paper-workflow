# 文档维护规则

本文档用于防止项目说明随时间漂移。

## 核心原则

只维护三类权威入口：
- README.md：人类入口
- AGENTS.md：AI 入口
- CONTEXT.md：运行时状态

详细说明一律放到 docs/。

## 什么时候改 README

当以下内容变化时改 README.md：
- 项目定位发生变化
- 目录结构发生变化
- 快速开始方式发生变化
- 需要新增人类入口说明

## 什么时候改 AGENTS

当以下内容变化时改 AGENTS.md：
- AI 执行规则变化
- 命名规范变化
- 输出位置变化
- 红线变化
- 论文生命周期规则变化

## 什么时候改 CONTEXT

当以下内容变化时改根 CONTEXT.md：
- 新建论文
- 切换论文
- 论文状态变更（活跃/暂停/已完成）

当以下内容变化时改论文级 CONTEXT.md：
- 论文阶段推进
- 新增文献
- 更新下一步计划
- 更新手稿版本

## 什么时候改 docs

当以下内容变化时改对应文档：
- 工作流调整 → docs/workflow.md
- 技能路由调整 → docs/skills-routing.md
- 环境依赖调整 → docs/setup.md
- 维护规则本身调整 → docs/maintenance.md

## 维护检查清单

定期检查：
1. README.md 是否仍然简洁
2. AGENTS.md 是否仍是唯一 AI 规则源
3. 是否还存在重复说明
4. 根 CONTEXT.md 是否只记录状态
5. 详细说明是否都落到了 docs/

## 常见错误

- 在 README.md 里放太长技能表
- 在 AGENTS.md 里重复放环境准备
- 同时维护多个重复规则文件
- 让根 CONTEXT.md 承担教程功能

## 本次归档处理

- `.claude/` 已不再作为新的权威运行目录
- 历史内容已复制到 `.archive/.claude-archive-2026-05-27/`
- `.claude/README.md` 已标注为归档说明
- 当前运行时 skills 以 `.agents/skills/` 为准
- 当前 agent 配置以 `.codex/agents/` 为准
