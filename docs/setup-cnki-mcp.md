# CNKI MCP Setup

CNKI skills (`cnki-search`, `cnki-download`, `cnki-export`, etc.) require Chrome DevTools MCP to interact with CNKI via browser automation.

## Required MCP Server

Chrome DevTools MCP must be configured before using any `cnki-*` skill.

The project includes a shared `.mcp.json` at the repository root. Claude Code reads it automatically on startup.

If the MCP server is unavailable, CNKI skills should stop and tell the user to configure it first.

## Verify

In Claude Code, run:

```
/mcp
```

Confirm that `chrome-devtools` appears in the server list with status "connected".

Or check from terminal:

```bash
claude mcp list
```

## Manual Setup

If `.mcp.json` is not picked up, add to your user-level Claude Code config:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

- **Claude Code**: `~/.claude/settings.json` → `mcpServers` key
- **Claude Desktop**: Settings → Developer → MCP Servers

## Prerequisites

- Node.js 18+ with `npx` available
- Chrome or Chromium browser installed
- Chrome remote debugging enabled (CNKI skills will prompt if needed)

## Notes

- Do not commit local Chrome profiles, cookies, tokens, or personal MCP paths.
- This file only contains the shared `chrome-devtools` MCP entry.
- Machine-specific overrides should go in user-level config, not in `.mcp.json`.

## CNKI CAPTCHA and Browser Profile Limitations

### Known Limitations

1. **CNKI CAPTCHA**: CNKI may trigger a block-puzzle CAPTCHA (`向右滑动完成验证`) for Chrome DevTools Protocol-level navigation. This is CNKI's anti-bot detection and cannot be bypassed programmatically.

2. **Fully automated CNKI navigation/search is not guaranteed**: The `navigate_page` MCP call to `kns.cnki.net` or `navi.cnki.net` may redirect to `verify/home?captchaType=blockPuzzle` regardless of manual login state.

3. **Browser profile/instance mismatch**: If `claude mcp list` shows `chrome-devtools` connected but `list_pages` only shows `about:blank` while the user has CNKI open in their normal Chrome, this indicates the MCP connection uses a different Chrome profile or browser instance than the user's manual browsing Chrome.

4. **Manual CAPTCHA solve does not carry over to MCP navigation**: Even if the user manually solves a CAPTCHA in a separate Chrome tab, the MCP-driven navigation triggers a fresh CAPTCHA check.

### Recommended Compliant Workflow

The recommended approach for CNKI skills is **manual navigation + MCP read-only extraction**:

1. User manually opens CNKI in the **same Chrome instance/profile** that MCP connects to.
2. User manually logs in and completes any CAPTCHA.
3. User manually navigates to search results, detail page, journal page, or TOC page.
4. MCP uses `take_snapshot` / `evaluate_script` to **read and extract** from the current page — without navigating to new CNKI URLs.
5. Skills must **not** bypass login, CAPTCHA, permissions, or download restrictions.

### What to Do If Blocked

- **MCP can see user's CNKI pages**: Proceed with read-only extraction.
- **MCP cannot see user's CNKI pages (only `about:blank`)**: Report profile/instance mismatch. Do not fabricate results.
- **CNKI redirects to CAPTCHA**: Stop and ask the user to complete the required manual action. Do not automate CAPTCHA solving.
- **Download blocked by permissions**: Report the permission limitation. Do not bypass.
