# MCP server setup

Beeper Desktop ships a built-in Model Context Protocol (MCP) server so that agents — Claude Desktop, Claude Code, Cursor, VS Code, Raycast, Windsurf, Warp, Codex, Gemini CLI, etc. — can search, send, and manage Beeper messages through standard MCP tools.

## Endpoints

| Transport | URL | Notes |
|---|---|---|
| Streamable HTTP (preferred) | `http://localhost:23373/v0/mcp` | Works with all modern MCP clients |
| Server-Sent Events (legacy) | `http://localhost:23373/v0/sse` | **Not compatible with Cloudflare Quick Tunnels** — use the streamable HTTP endpoint when tunneling |

Both require the Beeper Desktop API server to be running (Settings -> Developers -> Beeper Desktop API).

## Supported clients (per official docs)

Claude Desktop, Cursor, VS Code, Raycast, Windsurf, Warp, Codex, Gemini CLI. Claude Code is also supported via the `claude mcp add` CLI.

## Authentication

- Most modern MCP clients handle the OAuth flow automatically when they first connect to a streamable HTTP MCP endpoint. The Beeper server implements the MCP Authorization spec on top of its OAuth 2.0 + PKCE support.
- You can bypass OAuth entirely by sending an `Authorization: Bearer <token>` header. When a bearer token is present, the server skips MCP's OAuth flow and uses the token directly — useful for scripts or stdio-only clients.
- Discovery metadata: `GET /.well-known/oauth-authorization-server` (RFC 8414).

## Prerequisites

1. Beeper Desktop installed and running.
2. Settings -> Developers -> Beeper Desktop API enabled.
3. For manual-token setups, a token created under Settings -> Developers -> Approved connections -> `+`.
4. For stdio-only clients (old Claude Desktop builds), install Node.js and use `npx @beeper/mcp-remote` or `npx mcp-remote` as a bridge.

## Per-client setup

### Claude Code

```bash
# OAuth (default)
claude mcp add beeper http://localhost:23373/v0/mcp -t http -s user

# Local scope (this project only)
claude mcp add beeper http://localhost:23373/v0/mcp -t http -s local

# Manual token — bypasses OAuth
claude mcp add beeper http://localhost:23373/v0/mcp \
  -t http \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -s user
```

Verify: `claude mcp list`.

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "beeper": {
      "url": "http://localhost:23373/v0/mcp"
    }
  }
}
```

Restart Claude Desktop after editing.

### Cursor

Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "beeper": {
      "url": "http://localhost:23373/v0/mcp"
    }
  }
}
```

### VS Code

Create `.vscode/mcp.json` in your workspace (or edit the user-scope equivalent):

```json
{
  "mcpServers": {
    "beeper": {
      "httpUrl": "http://localhost:23373/v0/mcp",
      "timeout": 30000
    }
  }
}
```

Or use the deeplink helper from the Beeper docs to auto-populate.

### Windsurf

Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "beeper": {
      "url": "http://localhost:23373/v0/mcp"
    }
  }
}
```

### Gemini CLI

```bash
gemini mcp add --transport http beeper http://localhost:23373/v0/mcp
```

### stdio-only clients

If your client only supports stdio-transport MCP servers, use one of these Node.js bridges:

```json
{
  "mcpServers": {
    "beeper": {
      "command": "npx",
      "args": [
        "@beeper/mcp-remote",
        "http://localhost:23373/v0/mcp"
      ]
    }
  }
}
```

Or with the generic `mcp-remote`:

```json
{
  "mcpServers": {
    "beeper": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://localhost:23373/v0/mcp"
      ]
    }
  }
}
```

Requires Node.js on the PATH.

## Troubleshooting

- **"Connection refused"** — Beeper Desktop is closed or the API is disabled. Open the app, check Settings -> Developers -> Beeper Desktop API.
- **OAuth loops** — delete any stale credentials in your MCP client's auth store, or switch to manual bearer-token mode.
- **Streamable HTTP not supported** — fall back to the SSE endpoint `http://localhost:23373/v0/sse`, or use `@beeper/mcp-remote`.
- **Multiple tokens** — token revocation is managed in Settings -> Developers -> Approved connections.
