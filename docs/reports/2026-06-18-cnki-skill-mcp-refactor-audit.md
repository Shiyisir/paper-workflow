# CNKI Skill MCP Refactor — Stage 1 Audit

**Date**: 2026-06-18
**Branch**: `feat/cnki-skill-mcp-refactor`
**Stash**: `stash@{0}` — `wip: cnki skill mcp refactor` (applied, not popped)

## 1. Branch and Stash

- **Current branch**: `feat/cnki-skill-mcp-refactor` (from master `bcb058a`)
- **Stash applied**: `stash@{0}` — 24 files, 1356 insertions, 947 deletions
- **Conflicts**: none

## 2. Changed Files Summary

| Type | Count | Files |
|---|---|---|
| Modified SKILL.md | 11 | 10 cnki-* + nature-reviewer |
| Deleted JS scripts | 10 | search.js (×3), download.js, extract.js (×2), parse.js, batch-export.js, single-export.js, browse.js, navigate.js |
| Deleted reference docs | 2 | cnki-export/references/api.md, cnki-search/references/selectors.md |

## 3. CNKI SKILL.md Changes

| Skill | Execution Change | MCP Required | Has Preflight | evaluate_script refs | Risk |
|---|---|---|---|---|---|
| cnki-advanced-search | JS file → inline `mcp__chrome-devtools__evaluate_script` | Yes | **No** | References `evaluate_script` (MCP-native) | Low |
| cnki-download | JS file → inline MCP calls | Yes | **No** | References `evaluate_script` (MCP-native) | Low |
| cnki-export | JS files → inline `mcp__chrome-devtools__evaluate_script` | Yes | **No** | References `evaluate_script` (MCP-native) | Low |
| cnki-journal-index | JS file → inline `mcp__chrome-devtools__evaluate_script` | Yes | **No** | References `evaluate_script` (MCP-native) | Low |
| cnki-journal-search | JS file → inline `mcp__chrome-devtools__evaluate_script` | Yes | **No** | References `evaluate_script` (MCP-native) | Low |
| cnki-journal-toc | JS file → inline `mcp__chrome-devtools__evaluate_script` | Yes | **No** | References `evaluate_script` (MCP-native) | Low |
| cnki-navigate-pages | JS file → inline `evaluate_script` | Minimal | **No** | References `evaluate_script` (raw) | Low |
| cnki-paper-detail | JS file → inline `mcp__chrome-devtools__evaluate_script` | Yes | **No** | References `evaluate_script` (MCP-native) | Low |
| cnki-parse-results | JS file → inline `mcp__chrome-devtools__evaluate_script` | Yes | **No** | References `evaluate_script` (MCP-native) | Low |
| cnki-search | JS file → inline `mcp__chrome-devtools__evaluate_script` | Yes | **No** | References `evaluate_script` (MCP-native) | Low |

### Common Pattern

All skills follow the same refactor:
1. **Description/name**: Chinese → English
2. **JS logic**: External file (`scripts/*.js`) → Inline in SKILL.md as `mcp__chrome-devtools__evaluate_script` call with embedded function
3. **Pickle files**: Old references to `.pkl` cache files removed (logic now inlined)
4. **Structure**: Standardized with Arguments / Steps / Tool calls count

### Gap: No Preflight

None of the 10 CNKI skills includes a Preflight section. Should add:

```markdown
## Preflight

Before using this skill:
1. Confirm Chrome DevTools MCP is available (`/mcp`).
2. Confirm a Chrome tab can be inspected.
3. Confirm CNKI is accessible or can be opened.
4. If MCP is unavailable, stop and tell the user: see `docs/setup-cnki-mcp.md`.
5. Do not fall back to fabricated results.
```

### Gap: No MCP-reference in cnki-download and cnki-navigate-pages

`cnki-download` and `cnki-navigate-pages` have 0 `mcp__chrome-devtools` references. They use generic `evaluate_script` without namespace qualification. Should standardize.

## 4. Deleted JS Scripts

| File | Replacement Exists | Safe to Delete | Risk |
|---|---|---|---|
| cnki-advanced-search/scripts/search.js | Yes — inlined in SKILL.md | ✅ | Logic is complex; inline function must be tested |
| cnki-download/scripts/download.js | Yes — inlined in SKILL.md | ✅ | Download logic requires CNKI login state |
| cnki-export/scripts/batch-export.js | Yes — inlined in SKILL.md | ✅ | Batch export logic inlined; Zotero API interaction must work |
| cnki-export/scripts/single-export.js | Yes — merged into SKILL.md | ✅ | Single/batch merged into one skill |
| cnki-journal-index/scripts/extract.js | Yes — inlined in SKILL.md | ✅ | Journal evaluation metrics extraction inlined |
| cnki-journal-search/scripts/search.js | Yes — inlined in SKILL.md | ✅ | Journal search differs from paper search |
| cnki-journal-toc/scripts/browse.js | Yes — inlined in SKILL.md | ✅ | TOC browsing logic preserved inline |
| cnki-navigate-pages/scripts/navigate.js | Yes — inlined in SKILL.md | ✅ | Pagination/sorting logic inlined |
| cnki-paper-detail/scripts/extract.js | Yes — inlined in SKILL.md | ✅ | Most complex extractor — verify all fields preserved |
| cnki-parse-results/scripts/parse.js | Yes — inlined in SKILL.md | ✅ | Result parsing logic inlined |
| cnki-search/scripts/search.js | Yes — inlined in SKILL.md | ✅ | Core search logic inlined |

## 5. Deleted Reference Docs

| File | Safe to Delete | Reason |
|---|---|---|
| cnki-export/references/api.md | ✅ | Zotero API interaction now described inline in SKILL.md |
| cnki-search/references/selectors.md | ✅ | Selector knowledge embedded in inline evaluate_script functions |

No information loss — the deleted reference docs' contents are now embodied in the SKILL.md inline JS logic.

## 6. nature-reviewer Change

- **Change**: +4 lines adding Chinese trigger phrases to description
- **Related to CNKI MCP refactor?**: No — it's a trigger coverage improvement
- **Should be separate commit?**: Yes — unrelated to CNKI MCP refactor. Should be committed separately or at least noted as independent change.

## 7. Pollution Check

- paper-workflow files changed: **none**
- docs/superpowers changed: **none**
- .claude/settings.json changed: **none**

## 8. MCP Check

- `.mcp.json` valid: ✅ (verified with `python -m json.tool`)
- `docs/setup-cnki-mcp.md` exists: ✅
- `claude mcp list` result: not verified (no Claude Code CLI in test environment)

## 9. Tests

- paper-workflow tests: **481/481 passed**

## 10. Assessment

### Strengths
- Consistent refactor pattern across all 10 skills
- JS logic preserved (inlined, not lost)
- No paper-workflow pollution
- `evaluate_script` references now use MCP-native tool names
- All descriptions now in English (consistent with project standards)

### Gaps (must fix before commit)
1. **No Preflight section** — all 10 skills need MCP availability check before execution
2. **cnki-download, cnki-navigate-pages** — missing `mcp__chrome-devtools` namespace prefix
3. **No cross-reference to docs/setup-cnki-mcp.md** — skills should point users to setup guide
4. **nature-reviewer mixed in** — should be separate commit

### Risk Rating
- **Low**: Refactor is mechanical and consistent. JS logic preserved inline. No information loss detected.
- **Testing required**: All 10 skills need live CNKI testing before merge.

## 11. Recommended Next Step

Do not commit yet. Next stage should:
1. Add Preflight to all 10 CNKI SKILL.md files
2. Standardize MCP tool names (add `mcp__chrome-devtools__` prefix where missing)
3. Add `docs/setup-cnki-mcp.md` cross-reference
4. Separate nature-reviewer into its own commit
5. Test against live CNKI
