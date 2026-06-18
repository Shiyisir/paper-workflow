# CNKI + Root Changes Audit

**Date**: 2026-06-18
**Branch**: `wip/unrelated-cnki-root-changes`
**Stash**: `stash@{0}` (popped, no conflicts)

## 1. Summary

30 files changed: 1370 insertions, 953 deletions. Three categories:
- **A. CNKI skill refactoring** (23 files) — JS scripts deleted, SKILL.md rewritten
- **B. Root documentation** (6 files) — version bumps, gotchas, wording
- **C. Untracked local files** (5 files) — config, placeholder, stale docs

## 2. CNKI Skill Changes

| # | Skill | JS Deleted | SKILL.md Modified | Summary |
|---|---|---|---|---|
| 1 | cnki-advanced-search | search.js | +196 lines | Rewritten: Chinese→English, JS script→direct MCP |
| 2 | cnki-download | download.js | +110 lines | Same pattern |
| 3 | cnki-export | batch-export.js, single-export.js, api.md | +215 lines | Deleted references/api.md too |
| 4 | cnki-journal-index | extract.js | +166 lines | Same pattern |
| 5 | cnki-journal-search | search.js | +122 lines | Same pattern |
| 6 | cnki-journal-toc | browse.js | +181 lines | Same pattern |
| 7 | cnki-navigate-pages | navigate.js | +149 lines | Same pattern |
| 8 | cnki-paper-detail | extract.js | +194 lines | Same pattern |
| 9 | cnki-parse-results | parse.js | +108 lines | Same pattern |
| 10 | cnki-search | search.js, selectors.md | +139 lines | Deleted references/selectors.md too |
| 11 | nature-reviewer | — | +4 lines | Minor: added Chinese trigger phrases |

### Pattern

Every CNKI skill follows the same refactoring pattern:
1. **SKILL.md description**: Chinese → English
2. **Execution flow**: "inject JS via evaluate_script" → "direct MCP Chrome DevTools calls"
3. **JS scripts deleted**: All `scripts/*.js` removed (10 files total)
4. **Reference files deleted**: `references/api.md`, `references/selectors.md`

### Assessment

| Verdict | Reason |
|---|---|
| **Keep (but separate from paper-workflow)** | Refactoring is legitimate — moves from injected scripts to MCP-native approach. But this is a CNKI ecosystem change, not paper-workflow. Should be committed on its own branch, not mixed with v0.2 release. |
| JS deletions | Intentional — functionality moved into SKILL.md as MCP tool calls |
| SKILL.md rewrites | Substantial rewrites, new format is more structured |
| nature-reviewer change | Harmless, can keep |

### Risk

- If these CNKI skills are currently in use via `~/.aweskill/skills/` symlinks, deleting JS scripts will break them until the MCP approach is fully tested
- The rewrites haven't been tested against live CNKI

## 3. Root Documentation Changes

| File | Change | Verdict |
|---|---|---|
| `.gitignore` | Added `机器学习课程大作业/` and `papers/` | **Revert** — master already has better rules (`papers/*` + `!papers/README.md`) |
| `AGENTS.md` | v0.1.0-mvp → v0.1.2 | **Keep** — version bump is accurate |
| `CONTEXT.md` | v0.1.0-mvp → v0.1.2 | **Keep** — same |
| `README.md` | v0.1.2 mention, `--output-dir`→`--output`, 283→400 tests | **Mostly keep** — but test count is now 481, needs update |
| `docs/gotchas.md` | 4 new gotcha entries | **Keep** — all 4 are valuable lessons learned during v0.2 development |
| `docs/maintenance.md` | v0.1.0-mvp → v0.1.2 | **Keep** — version bump |

### Gotchas added (all worth keeping)

1. 严禁编造文献 — don't fabricate citations
2. spec 分类表必须全文交叉核验 — cross-validate spec tables
3. skill_handoff done_conditions 必须拆两层 — handoff_done vs stage_done
4. spec-first 比 code-first 省时间 — design-first lesson

## 4. Untracked / Local Files

| File | Decision | Reason |
|---|---|---|
| `.claude/settings.json` | **Delete / add to .gitignore** | Chrome DevTools MCP config — belongs in `C:\Users\易朝亮\.claude\settings.json`, not project repo |
| `CLAUDE.md` | **Delete** | Single line, redundant. CLAUDE.md already exists at project root |
| `docs/superpowers/plans/2026-06-12-paper-workflow-implementation-plan.md` | **Move to docs/design/** | Valuable — v0.1 implementation plan |
| `docs/superpowers/plans/2026-06-16-paper-workflow-v0.2-stage-executor-implementation-plan.md` | **Move to docs/design/** | Valuable — v0.2 stage executor plan |
| `docs/superpowers/specs/2026-06-16-paper-workflow-v0.2-stage-executor.md` | **Move to docs/design/** | Valuable — v0.2 stage executor spec |

Note: These 3 docs are in `docs/superpowers/` which no longer exists on master. After rebasing this branch onto master, they'd need to go to `docs/design/`.

## 5. Risks

1. **CNKI skills untested**: Rewrites are substantial but never tested against live CNKI. If CNKI search is needed soon, test first.
2. **Branch divergence**: This branch was created from pre-reorg master. Merging back would reintroduce `docs/superpowers/` structure. Need to either rebase onto current master or cherry-pick.
3. **.gitignore conflict**: This branch adds `papers/` and `机器学习课程大作业/` to gitignore, but master has `papers/*` with negation rules. Master's version is correct.

## 6. Recommended Next Step

**Split into 3 separate branches:**

### Branch 1: `feat/cnki-skill-mcp-refactor`
- CNKI SKILL.md rewrites + JS deletions
- Test against live CNKI before merging
- Commit separately from paper-workflow

### Branch 2: `docs/root-doc-updates`
- AGENTS.md, CONTEXT.md, README.md version bumps
- docs/gotchas.md additions
- docs/maintenance.md update
- **Rebase onto current master first** to pick up directory reorg
- Drop .gitignore changes (master's version is better)

### Branch 3: Delete local files
- `.claude/settings.json` → delete from repo
- `CLAUDE.md` → delete (redundant)
- Move 3 untracked docs to `docs/design/` (after rebase)

**Current branch `wip/unrelated-cnki-root-changes` can be deleted after splitting.**
