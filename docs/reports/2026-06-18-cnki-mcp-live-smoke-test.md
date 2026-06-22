# CNKI MCP Live Smoke Test

## 1. Environment

- **Branch**: `feat/cnki-skill-mcp-refactor`
- **Commit**: `d98da81`
- **Date**: 2026-06-18
- **MCP config**: `.mcp.json` — valid, `chrome-devtools` defined
- **Chrome DevTools MCP status**: `⏸ Pending approval` (`npx -y chrome-devtools-mcp@latest`)
- **CNKI login status**: not tested (requires interactive browser)

## 2. Test Matrix

| Skill | Test Action | Result | Notes | Required Fix |
|---|---|---|---|---|
| cnki-search | Structural check | ✅ PASS | Preflight + setup ref + MCP tool refs present | None |
| cnki-download | Structural check | ✅ PASS | MCP namespace fixed, Preflight present | None |
| cnki-export | Structural check | ✅ PASS | Zotero API inline, Preflight present | None |
| cnki-advanced-search | Structural check | ✅ PASS | Preflight + setup ref present | None |
| cnki-journal-search | Structural check | ✅ PASS | Preflight + MCP refs present | None |
| cnki-journal-index | Structural check | ✅ PASS | 4 MCP tool refs, Preflight present | None |
| cnki-journal-toc | Structural check | ✅ PASS | 4 MCP tool refs, Preflight present | None |
| cnki-navigate-pages | Structural check | ✅ PASS | MCP namespace fixed, Preflight present | None |
| cnki-paper-detail | Structural check | ✅ PASS | 5 MCP tool refs, Preflight present | None |
| cnki-parse-results | Structural check | ✅ PASS | 3 MCP tool refs, Preflight present | None |

**All 10 skills pass structural validation.** Live CNKI interaction blocked by MCP approval.

## 3. Live Test Blocks

| Skill | Failure Type | Cause | Fix Needed |
|---|---|---|---|
| All 10 skills | `mcp_pending_approval` | Chrome DevTools MCP requires user approval in Claude Code (`/mcp` → approve) | User action: run `/mcp` in CC and approve `chrome-devtools` |

## 4. Compliance Notes

- No login bypass: N/A (MCP not connected)
- No CAPTCHA bypass: N/A
- No permission bypass: N/A
- No fabricated results: ✅ — no results generated, structural validation only

## 5. Structural Validation Results

| Check | Result |
|---|---|
| All 10 skills have Preflight | ✅ |
| All 10 skills reference docs/setup-cnki-mcp.md | ✅ |
| MCP namespace standardized | ✅ |
| cnki-download MCP prefix fixed | ✅ |
| cnki-navigate-pages MCP prefix fixed | ✅ |
| No bare `evaluate_script` (without namespace) | ✅ |
| JS replacements inlined in SKILL.md | ✅ (confirmed by git diff, all 10 scripts replaced) |
| Reference docs inlined | ✅ (api.md → SKILL.md, selectors.md → SKILL.md) |

## 6. Summary

- **Structural**: All 10 CNKI skills pass validation. No remaining gaps from Stage 1 audit.
- **Live testing**: Blocked by Chrome DevTools MCP pending approval. Once approved in Claude Code (`/mcp`), all 10 skills should be testable.
- **No pickle deletion**: Earlier report incorrectly mentioned a pickle file — only JS scripts and markdown reference docs were deleted.
- **Risk**: The inline JS functions have not been verified against live CNKI DOM. CNKI's page structure may have changed since the refactor. First live test should verify selectors.

## 7. Recommended Next Step

1. Approve `chrome-devtools` MCP in Claude Code (`/mcp` → approve)
2. Open CNKI in Chrome and log in if needed
3. Run live smoke test for each skill (start with cnki-search)
4. Report any selector changes or failures
5. After live test passes → merge to master
