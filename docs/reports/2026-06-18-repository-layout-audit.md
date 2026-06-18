# Repository Layout Audit

**Date**: 2026-06-18
**Branch**: `docs/root-doc-updates`

## 1. Summary

全仓库目录审计。除了已知已修复的 `docs/superpowers/`，未发现其他旧目录、错位目录、tracked 残留或 ignored 规则失效。

## 2. Top-level Directory Check

```
.agents/          ← agent skill 定义
.claude/          ← Claude skill 源码
.code-review-graph/ ← 图谱缓存（不提交）
.codex/           ← Codex agent 定义
_template/        ← 论文项目模板
docs/             ← 项目文档
papers/           ← 本地论文项目（默认忽略）
```

无异常目录。`机器学习课程大作业/`、`paper-tests/`、临时输出目录均不存在。

## 3. Tracked Legacy Paths

`docs/superpowers/`：**无**。已通过 rebase 到 master 消除。

`papers/` 跟踪文件：仅 2 个
- `papers/README.md`
- `papers/_reference/README.md`

论文项目内容全部被 `.gitignore` 忽略，符合预期。

## 4. Untracked / Ignored Files

未跟踪文件：无（`git status --short --untracked-files=all` 为空）。

Ignore 规则验证：

| 路径 | Ignored by | 状态 |
|---|---|---|
| `papers/qdn-esv-hwb/` | `.gitignore:7 papers/*` | ✅ |
| `papers/ml-rainfall-prediction/` | `.gitignore:7 papers/*` | ✅ |
| `papers/_reference/混凝土课程作业/` | `.gitignore:10 papers/_reference/*` | ✅ |
| `.claude/settings.json` | 不存在 | ✅ |

## 5. Old Path References

### 5.1 `docs/superpowers` 引用

仅出现在 `docs/reports/2026-06-18-cnki-root-changes-audit.md` 中，属于审计报告描述旧路径的历史文本。**Severity: Low**。可接受——审计报告本身就是为了记录迁移过程。

### 5.2 `D:/paper-tests` 引用

仅 1 处：`docs/reports/2026-06-18-paper-workflow-v0.2-real-paper-test.md` 记录测试项目的原始路径。**Severity: Low**。可更新为 `papers/qdn-esv-hwb`。

### 5.3 `机器学习课程大作业` 引用

2 处：smoke-test-2 报告（历史测试记录）和 CNKI 审计报告。**Severity: Low**。smoke-test-2 是旧版测试报告，路径为历史记录；审计报告描述的是旧 `.gitignore` 变更。

### 5.4 `qdn-esv-hwb` / `ml-rainfall-prediction` 引用

均为报告或 spec 中的测试项目名称引用，非路径引用。**Severity: None**。

## 6. Tracked Binary / Large Files

共 52 个 PNG 文件，分为三类：

| 来源 | 数量 | 判定 |
|---|---|---|
| `.agents/skills/nature-figure/assets/` | 49 | ✅ 合法 — nature-figure skill 的图表参考集 |
| `.claude/skills/paper-workflow/tests/fixtures/` | 2 | ✅ 合法 — 测试 fixture |
| `.agents/skills/nature-figure/assets/figures4papers/` | 31 | ✅ 合法 — figures4papers 参考素材 |

无 docx、PDF、zip 被跟踪。所有二进制均为 skill 资产或测试 fixture，非论文内容。`.gitignore` 正确排除了 `papers/` 下的二进制。

## 7. Problems Found

| # | Problem | Severity | Suggested Fix |
|---|---|---|---|
| 1 | Audit report 中 `docs/superpowers` 历史引用 | Low | 不需要修复——审计报告描述的就是迁移过程 |
| 2 | Real-paper-test 报告引用 `D:/paper-tests/qdn-esv-hwb` | Low | 更新为 `papers/qdn-esv-hwb` |
| 3 | Smoke-test-2 报告引用 `机器学习课程大作业` 旧路径 | Low | 可以更新为 `papers/_reference/混凝土课程作业/` |
| 4 | CNKI audit 报告中的 `docs/superpowers` 和 branch divergence 描述已过时 | Low | 可追加注释说明分支已 rebase |

## 8. Safe to Merge?

**是。** `docs/root-doc-updates` 可以安全合并到 master。

## 9. Recommended Next Steps

1. 合并 `docs/root-doc-updates` → `master`
2. 处理 `feat/cnki-skill-mcp-refactor`（从 stash 恢复 CNKI 重构）
3. 可选：更新旧报告中的历史路径引用（severity low，不阻塞合并）
