# CNKI MCP Dual-mode Validation

## 1. Environment

- **Branch**: `feat/cnki-skill-mcp-refactor`
- **Commit**: `7434a98`
- **Date**: 2026-06-22
- **MCP config**: `.mcp.json` — valid
- **Chrome DevTools MCP status**: Connected
- **User CNKI login status**: Unknown (user may be logged in on separate Chrome instance)
- **Can MCP see manually opened CNKI tabs**: **No** — only `about:blank` visible

## 2. Dual-mode Definition

| Mode | Description | Tested? |
|---|---|---|
| Manual navigation | User manually navigates CNKI in Chrome | Not verified — MCP cannot see user's tabs |
| MCP read-only | MCP reads existing page without CNKI navigation | Not possible — no CNKI pages visible |
| Automatic CNKI navigation | MCP navigates to CNKI URLs | Blocked by CAPTCHA (Stage 3.1, 3.2) |
| CAPTCHA bypass | N/A | Not attempted (compliance) |

## 3. Page Visibility Check

MCP `list_pages` result: only 1 page — `about:blank`. No CNKI pages detected.

This indicates one of:
1. User has not manually opened CNKI in Chrome
2. MCP's Chrome DevTools connection uses a different Chrome profile/instance than the user's browsing Chrome
3. User's CNKI tabs are in a different window that MCP cannot see

## 4. Root Cause: Profile/Instance Mismatch

The `chrome-devtools-mcp` server launches or connects to a specific Chrome instance. If the user manually opens CNKI in their regular Chrome browser, and MCP connects to a different Chrome instance (e.g., a headless or separate debugging instance), the tabs will not be shared.

**Resolution needed**: The user must ensure MCP connects to the SAME Chrome instance they use for manual CNKI browsing, or manually open CNKI pages within the MCP-connected Chrome instance.

## 5. Read-only Test Matrix

| Skill | Result | Evidence |
|---|---|---|
| All skills | `dual_mode_blocked_by_profile_mismatch` | MCP sees only `about:blank`, no CNKI pages |

## 6. Automatic Mode Status

| Skill | Status |
|---|---|
| All CNKI navigation skills | `blocked_by_captcha` (Stage 3.1, 3.2 confirmed) |

## 7. What Was Verified Across All Stages

| Stage | Finding |
|---|---|
| Stage 1 | Structural audit: all 10 skills have inline JS, Preflight, setup reference ✅ |
| Stage 2 | Fixed: Preflight added, MCP namespace standardized, nature-reviewer separated ✅ |
| Stage 3 | Chrome DevTools MCP tools work (`list_pages`, `navigate_page`, `take_snapshot`, `evaluate_script`) ✅ |
| Stage 3.1 | CNKI blocks MCP/CDP navigation with CAPTCHA ❌ |
| Stage 3.2 | Manual CAPTCHA solve in separate tab does not carry over ❌ |
| Stage 3.3 | Dual-mode blocked: MCP cannot see user's manually opened CNKI tabs ❌ |

## 8. How Dual-mode Could Work (Untested)

If the user opens CNKI pages within the MCP-connected Chrome instance:
1. User manually navigates to CNKI in the MCP Chrome instance (solving CAPTCHA if needed)
2. MCP uses `take_snapshot` / `evaluate_script` to read from the existing page
3. MCP does NOT navigate to new CNKI URLs (avoids CAPTCHA trigger)
4. After reading, MCP can extract and return structured data

This was not testable in the current environment because the user's Chrome and MCP's Chrome appear to be different instances.

## 9. Compliance

- Login bypass: None
- CAPTCHA bypass: None
- Permission bypass: None
- Batch download: None
- Fabricated results: None

## 10. Pollution Check

All clean — no paper-workflow, superpowers, settings.json, or papers changes.

## 11. Tests

- `.mcp.json` valid: ✅
- paper-workflow tests: 481/481 passed

## 12. Git Status

Clean

## 13. Merge Recommendation

The CNKI skill refactor is structurally sound (Stage 1+2 audits pass, all 10 skills have Preflight + MCP namespace + setup reference). MCP connectivity is verified.

The live test is blocked by:
1. CNKI CAPTCHA (environmental, not a code bug)
2. Chrome profile mismatch (setup issue, not a code bug)

Neither of these is a reason to block merge. The refactor branch can proceed to merge. The dual-mode workflow should be documented in `docs/setup-cnki-mcp.md` as the recommended approach.
