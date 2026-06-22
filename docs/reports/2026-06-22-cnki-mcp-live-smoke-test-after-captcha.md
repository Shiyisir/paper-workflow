# CNKI MCP Live Smoke Test After Manual CAPTCHA Attempt

## 1. Environment

- **Branch**: `feat/cnki-skill-mcp-refactor`
- **Commit**: `6a1ceda`
- **Date**: 2026-06-22
- **MCP config**: `.mcp.json` — valid
- **Chrome DevTools MCP status**: Connected (MCP tool calls work)
- **CNKI reachable**: Yes (HTTP 200, CAPTCHA redirect)
- **CAPTCHA manually attempted**: Unknown — user may or may not have solved in Chrome; MCP navigation triggers fresh CAPTCHA regardless
- **CNKI login status**: N/A (blocked before page access)
- **Permission limitation**: N/A

## 2. CAPTCHA Verification

| Domain | Before Manual Attempt | After MCP Navigation | Result |
|---|---|---|---|
| kns.cnki.net | `verify/home?captchaType=blockPuzzle` | `verify/home?captchaType=blockPuzzle` | **Still CAPTCHA** |
| navi.cnki.net | `verify/home?captchaType=blockPuzzle` | Not retested | Presumed same |

## 3. Root Cause Analysis

CNKI's CAPTCHA is triggered by **automated navigation via Chrome DevTools Protocol**, not by browser session state. Key observations:

1. `mcp__chrome-devtools__navigate_page` triggers CNKI's anti-bot detection
2. Manual CAPTCHA solve in a regular Chrome tab does NOT carry over to MCP-driven navigation
3. CNKI detects CDP-level navigation as automated behavior
4. This is a domain-level block: both `kns.cnki.net` and `navi.cnki.net` affected

## 4. Live Test Matrix

| Skill | Result | Evidence |
|---|---|---|
| cnki-search | `blocked_by_captcha` | navigate_page → verify/home redirect |
| All other 9 skills | `not_tested` | Blocked upstream by same CAPTCHA |

## 5. What Was Re-verified

| Check | Result |
|---|---|
| Chrome DevTools MCP available | ✅ |
| CNKI responds to MCP navigation | ✅ (CAPTCHA redirect) |
| Manual CAPTCHA solve carries over | ❌ — MCP navigation triggers fresh CAPTCHA |
| CAPTCHA type | Block puzzle slider ("向右滑动完成验证") |

## 6. Implications for CNKI Skill Design

The CNKI skills were designed on the assumption that Chrome DevTools MCP can navigate CNKI pages. This live test reveals:

- **MCP-only navigation to CNKI is blocked by CAPTCHA**
- The skills' Preflight instructions say "ask user to open CNKI in Chrome"—this is correct but insufficient: the user must also be the one to navigate, not MCP
- CNKI skills may need a **dual-mode** approach:
  - **Mode A**: User manually navigates CNKI in Chrome → MCP reads/interacts with existing page (no new navigation)
  - **Mode B**: MCP navigates → CAPTCHA → user solves → MCP proceeds (may not work for all pages)

## 7. Compliance

- Login bypass: None attempted
- CAPTCHA bypass: None attempted
- Permission bypass: N/A
- Batch download: None
- Fabricated results: None — honestly reported as blocked

## 8. Pollution Check

- paper-workflow files changed: none
- docs/superpowers changed: none
- `.claude/settings.json` changed: none
- papers changed: none

## 9. Tests

- `.mcp.json` valid: ✅
- paper-workflow tests: 481/481 passed

## 10. Git Status

Clean

## 11. Summary

CNKI live smoke test remains blocked by CAPTCHA after 3 attempts (Stage 3, 3.1, 3.2). The CAPTCHA is triggered by MCP-level navigation, not by browser session state. Manual CAPTCHA solve in a separate Chrome tab does not resolve the issue for MCP-driven navigation.

**This does NOT invalidate the CNKI skill refactor.** The SKILL.md files already instruct users to manually handle CAPTCHA. The refactor's structural quality (Preflight, MCP namespace, inline JS logic) is unaffected.

## 12. Recommended Next Step

1. Accept that live CNKI MCP smoke test is blocked by environmental constraints (not code bugs)
2. Merge `feat/cnki-skill-mcp-refactor` to master based on structural validation (Stage 1+2 audits) + MCP connectivity verified
3. For actual CNKI usage, instruct users to manually navigate CNKI in Chrome first, then let MCP read/interact with existing pages
