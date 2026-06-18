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
