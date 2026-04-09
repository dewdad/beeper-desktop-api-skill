# beeper-desktop-api-skill

Agent Skill that documents the **[Beeper Desktop API](https://developers.beeper.com/desktop-api)** — the local HTTP + WebSocket + MCP server shipped by Beeper Desktop that lets code read, search, send, edit, react to, and stream messages across WhatsApp, iMessage, Signal, Telegram, Twitter/X, Discord, and every other network connected to the Beeper client.

Load this skill into Claude Code, Cursor, Codex CLI, OpenCode, Gemini CLI, or any agent that speaks the [`SKILL.md` standard](https://skills.sh/docs) to get a senior engineer who already knows every endpoint, SDK method, WebSocket event, MCP setup flow, and deployment gotcha for the Beeper Desktop API.

## What it covers

| Area | File |
|---|---|
| Entry + quick start + REST summary + auth + guardrails | [`SKILL.md`](skills/beeper-desktop-api/SKILL.md) |
| Every `/v1/*` REST endpoint with full request/response schemas and curl examples | [`references/endpoints-rest.md`](skills/beeper-desktop-api/references/endpoints-rest.md) |
| `@beeper/desktop-api` (TypeScript SDK) | [`references/sdk-typescript.md`](skills/beeper-desktop-api/references/sdk-typescript.md) |
| `beeper_desktop_api` (Python SDK, sync + async) | [`references/sdk-python.md`](skills/beeper-desktop-api/references/sdk-python.md) |
| `github.com/beeper/desktop-api-go` (Go SDK) | [`references/sdk-go.md`](skills/beeper-desktop-api/references/sdk-go.md) |
| Shared object schemas (Account, Chat, Message, Attachment, Reaction, Participant) | [`references/schemas.md`](skills/beeper-desktop-api/references/schemas.md) |
| Experimental WebSocket realtime events (`ws://localhost:23373/v1/ws`) | [`references/websocket.md`](skills/beeper-desktop-api/references/websocket.md) |
| Built-in MCP server setup for Claude Desktop, Claude Code, Cursor, VS Code, Raycast, Windsurf, Warp, Codex, Gemini CLI | [`references/mcp-server.md`](skills/beeper-desktop-api/references/mcp-server.md) |
| In-app token creation, OAuth 2.0 + PKCE, `/oauth/introspect`, MCP auth bypass | [`references/authentication.md`](skills/beeper-desktop-api/references/authentication.md) |
| HTTP status codes, error envelope shape, SDK exception mapping, retry guidance | [`references/errors.md`](skills/beeper-desktop-api/references/errors.md) |
| Remote access (Advanced Settings), `0.0.0.0` binding, `X-Forwarded-*` headers, Cloudflare Quick Tunnels + SSE caveat | [`references/remote-access.md`](skills/beeper-desktop-api/references/remote-access.md) |
| `bbctl` (Beeper Bridge Manager) overview and official bridge identifier list | [`references/bridges-self-hosting.md`](skills/beeper-desktop-api/references/bridges-self-hosting.md) |
| 10 end-to-end recipes: bulk DM, export chat to CSV, image attachment send, watch a chat via WebSocket, daily unread digest, etc. | [`references/cookbook.md`](skills/beeper-desktop-api/references/cookbook.md) |

## Install

Pick whichever your agent supports.

### `skills` CLI (skills.sh)

```bash
npx skills add gfsaaser24/beeper-desktop-api-skill
```

Optional flags: `-g` to install globally (to `~/<agent>/skills/`), otherwise the skill lands in your current project under `./<agent>/skills/beeper-desktop-api/`.

### Claude Code — symlink into the user skills directory

```bash
# macOS/Linux
git clone https://github.com/gfsaaser24/beeper-desktop-api-skill.git
ln -s "$PWD/beeper-desktop-api-skill/skills/beeper-desktop-api" ~/.claude/skills/beeper-desktop-api

# Windows PowerShell
git clone https://github.com/gfsaaser24/beeper-desktop-api-skill.git
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\beeper-desktop-api" `
  -Target "$PWD\beeper-desktop-api-skill\skills\beeper-desktop-api"
```

Restart Claude Code and the skill activates automatically whenever a prompt mentions Beeper, chat networks, or the relevant endpoints.

### Manual copy

Copy the `skills/beeper-desktop-api/` directory into wherever your agent looks for skills (`.claude/skills/`, `.cursor/skills/`, `.codex/skills/`, `.agents/skills/`, etc.). Only `SKILL.md` is strictly required; the `references/` subfolder unlocks the full reference library.

## Prerequisites

To actually run code against the Beeper Desktop API after loading this skill:

1. Install [Beeper Desktop](https://www.beeper.com/download) v4.1.169 or newer.
2. Open Beeper → **Settings → Developers → Beeper Desktop API** and enable the server.
3. In **Settings → Developers → Approved connections** click **+** to mint an access token.
4. Export it for the SDKs: `export BEEPER_ACCESS_TOKEN="your_token_here"`.

## Quick smoke test

Once Beeper Desktop is running with the API enabled:

```bash
curl http://localhost:23373/v1/info \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

A `200` response with `server.status: "ok"` means you're good to go.

## Versioning and sources

This skill targets the **`/v1/*`** RESTful surface introduced in Beeper Desktop **4.1.294** (2025-10-16). All `/v0/*` endpoints are listed purely as deprecation cross-references.

Content is fact-checked against:

- https://developers.beeper.com/desktop-api (operation pages)
- https://developers.beeper.com/llms-small.txt (concise protocol summary)
- https://developers.beeper.com/desktop-api/auth (authentication)
- https://developers.beeper.com/desktop-api/websocket-experimental (realtime events)
- https://developers.beeper.com/desktop-api/mcp (MCP server)
- https://developers.beeper.com/desktop-api-reference/typescript, `.../python`, `.../go` (SDK references)

If Beeper ships breaking changes, open an issue or PR against this repo.

## Repository layout (skills.sh-compatible)

```
beeper-desktop-api-skill/
├── README.md                    # (this file)
├── LICENSE                      # MIT
└── skills/
    └── beeper-desktop-api/
        ├── SKILL.md             # frontmatter + entry doc
        └── references/          # progressive-disclosure reference library
            ├── endpoints-rest.md
            ├── sdk-typescript.md
            ├── sdk-python.md
            ├── sdk-go.md
            ├── schemas.md
            ├── websocket.md
            ├── mcp-server.md
            ├── authentication.md
            ├── errors.md
            ├── remote-access.md
            ├── bridges-self-hosting.md
            └── cookbook.md
```

`SKILL.md` is the only file the `skills` CLI strictly requires. The `references/` files are loaded on demand by the agent whenever it needs deep detail on a specific area — the progressive-disclosure pattern keeps context lean.

## Security

- Treat your `BEEPER_ACCESS_TOKEN` like an account credential. Anyone holding it can read and send messages on every network connected to your Beeper client.
- Prefer per-client OAuth tokens (revocable individually under **Settings → Developers → Approved connections**) over sharing a single long-lived token.
- The skill itself is plain Markdown — no executable code, no runtime side effects.

## License

[MIT](LICENSE).

## Not affiliated with Beeper

This is an unofficial, community-maintained skill. It documents Beeper's public Desktop API based on the official developer docs at https://developers.beeper.com/ but is not endorsed by or affiliated with Beeper / Automattic.
