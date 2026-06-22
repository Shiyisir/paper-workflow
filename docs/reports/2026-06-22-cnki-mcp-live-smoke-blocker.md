# CNKI MCP Live Smoke Test — Blocker Report

## 1. Environment

- **Branch**: `feat/cnki-skill-mcp-refactor`
- **Commit**: `cf4837e`
- **Date**: 2026-06-22
- **MCP config**: `.mcp.json` — valid
- **Chrome DevTools MCP status**: Connected (via `mcp__chrome-devtools__*` tools, despite CLI showing "Pending approval")
- **CNKI reachable**: Yes (HTTP 200, but redirects to CAPTCHA)
- **CNKI login status**: N/A (blocked before login)
- **CAPTCHA encountered**: Yes — block puzzle slider on both `kns.cnki.net` and `navi.cnki.net`
- **Permission limitation**: N/A (blocked before page access)

## 2. Test Attempts

| Attempt | URL | Result |
|---|---|---|
| 1 | `https://kns.cnki.net/kns8s/search` | Redirect → `verify/home?captchaType=blockPuzzle` |
| 2 | `https://navi.cnki.net/knavi/` | Redirect → `verify/home?captchaType=blockPuzzle` |

Both attempts hit the same CAPTCHA wall. The CAPTCHA type is "block puzzle" (slider verification).

## 3. Test Matrix

| Skill | Target URL | Result | Evidence |
|---|---|---|---|
| cnki-search | kns.cnki.net/kns8s/search | `blocked_by_captcha` | Redirect to verify/home page |
| cnki-parse-results | (requires search results) | `blocked_by_captcha` | Same redirect |
| cnki-paper-detail | (requires paper URL) | `blocked_by_captcha` | All kns.cnki.net paths redirect |
| cnki-advanced-search | kns.cnki.net/kns8s/advsearch | `not_tested` | Blocked by same domain CAPTCHA |
| cnki-journal-search | kns.cnki.net/kns8s/search | `not_tested` | Blocked |
| cnki-journal-index | navi.cnki.net/knavi/detail | `blocked_by_captcha` | Redirect to verify/home |
| cnki-journal-toc | navi.cnki.net/knavi/ | `blocked_by_captcha` | Same redirect |
| cnki-navigate-pages | (requires results page) | `not_tested` | Blocked upstream |
| cnki-export | (requires detail page) | `not_tested` | Blocked upstream |
| cnki-download | (requires detail page) | `not_tested` | Blocked upstream |

## 4. Observations

- CNKI CAPTCHA is domain-wide: any navigation to `kns.cnki.net` or `navi.cnki.net` triggers the block puzzle.
- The CAPTCHA page title is "安全验证" with text "向右滑动完成验证".
- This is consistent with known CNKI anti-bot behavior — automated MCP access triggers it.
- The CNKI SKILL.md files already address CAPTCHA handling: "If CAPTCHA appears, tell user to solve it manually."

## 5. What Was Verified

| Check | Result |
|---|---|
| Chrome DevTools MCP available | Yes — `list_pages`, `navigate_page`, `take_snapshot`, `close_page` all work |
| CNKI reachable from MCP | Yes (200 response, CAPTCHA redirect) |
| SKILL.md CAPTCHA handling instructions exist | Yes — Preflight step 4: "If CNKI requires login, ask the user to complete login manually" and Gotchas references |
| `.mcp.json` valid | Yes |

## 6. Compliance

- Login bypass: N/A (blocked before login)
- CAPTCHA bypass: None attempted — stopped at first CAPTCHA
- Permission bypass: N/A
- Batch download: None
- Fabricated results: None

## 7. What This Does NOT Mean

- ❌ Does not mean the CNKI skill refactor is broken
- ❌ Does not mean MCP setup is wrong
- ✅ Does mean: CNKI live smoke test requires the user to manually solve one CAPTCHA in Chrome before automated MCP access can proceed

## 8. Recommended Fix

The user should:
1. Open CNKI manually in Chrome (via the same Chrome instance MCP connects to)
2. Solve the CAPTCHA manually (slide to verify)
3. After CAPTCHA is solved, the session cookie persists in Chrome
4. Then MCP can navigate CNKI pages without hitting CAPTCHA (for the session duration)

This is a one-time manual step per Chrome session — not a blocker for the CNKI skill refactor merge.

## 9. Commits Created

None yet — this is a blocker report, not a code change.

## 10. Recommendation

The CNKI CAPTCHA is an environmental constraint, not a skill bug. The refactor branch (`feat/cnki-skill-mcp-refactor`) can proceed to merge after review. Live smoke test should be re-attempted after manual CAPTCHA resolution in Chrome.
