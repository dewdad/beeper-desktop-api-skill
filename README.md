# beeper-desktop-api-skill

Agent Skill that documents the **[Beeper Desktop API](https://developers.beeper.com/desktop-api)** — the local HTTP + WebSocket + MCP server shipped by Beeper Desktop that lets code read, search, send, edit, react to, and stream messages across WhatsApp, iMessage, Signal, Telegram, Twitter/X, Discord, and every other network connected to the Beeper client.

Load this skill into Claude Code, Cursor, Codex CLI, OpenCode, Gemini CLI, or any agent that speaks the [`SKILL.md` standard](https://skills.sh/docs) to get a senior engineer who already knows every endpoint, SDK method, WebSocket event, MCP setup flow, and deployment gotcha for the Beeper Desktop API.

## Two skills in this repo

| Skill | What it's for |
|---|---|
| [`beeper-desktop-api`](skills/beeper-desktop-api/SKILL.md) | **Knowledge base.** Every REST endpoint, SDK (TS/Python/Go), WebSocket event, MCP setup, auth flow, and gotcha. Load it whenever you write code against the Beeper Desktop API. |
| [`beeper-messaging-manager`](skills/beeper-messaging-manager/SKILL.md) | **Turnkey automation.** A one-command installer plus two standing automations that make your agent *manage* your messaging: a supervised realtime alert watcher and a 3×/day ranked digest. Builds on `beeper-desktop-api`. |

If you just want to **build against the API**, use the first skill. If you want your agent to **watch and digest your messages for you** with minimal setup, run the installer that ships with the second:

```bash
python3 skills/beeper-messaging-manager/scripts/install.py --dry-run   # preview
python3 skills/beeper-messaging-manager/scripts/install.py             # do it
```

The installer detects your OS (Linux/macOS/Windows) and host agent (Hermes/OpenCode/generic), verifies Beeper Desktop is reachable, materializes an isolated automation dir + venv, supervises the watcher (systemd/launchd), registers or prints the digest schedule, and self-tests the alert logic — automating what it can and printing exact manual steps for the rest. See its [SKILL.md](skills/beeper-messaging-manager/SKILL.md) for the full model.

## What the API skill covers

| Area | File |
|---|---|
| Entry + quick start + REST summary + auth + guardrails | [`SKILL.md`](skills/beeper-desktop-api/SKILL.md) |
| Every `/v1/*` REST endpoint with full request/response schemas and curl examples | [`references/endpoints-rest.md`](skills/beeper-desktop-api/references/endpoints-rest.md) |
| `@beeper/desktop-api` (TypeScript SDK) | [`references/sdk-typescript.md`](skills/beeper-desktop-api/references/sdk-typescript.md) |
| `beeper_desktop_api` (Python SDK, sync + async) | [`references/sdk-python.md`](skills/beeper-desktop-api/references/sdk-python.md) |
| `github.com/beeper/desktop-api-go` (Go SDK) | [`references/sdk-go.md`](skills/beeper-desktop-api/references/sdk-go.md) |
| Shared object schemas (Account, Chat, Message, Attachment, Reaction, Participant) | [`references/schemas.md`](skills/beeper-desktop-api/references/schemas.md) |
| Experimental native polls through Beeper-backed chats, with dry-run-first helper | [`references/polls.md`](skills/beeper-desktop-api/references/polls.md) |
| Experimental WebSocket realtime events (`ws://localhost:23373/v1/ws`) | [`references/websocket.md`](skills/beeper-desktop-api/references/websocket.md) |
| Built-in MCP server setup for Claude Desktop, Claude Code, Cursor, VS Code, Raycast, Windsurf, Warp, Codex, Gemini CLI | [`references/mcp-server.md`](skills/beeper-desktop-api/references/mcp-server.md) |
| In-app token creation, OAuth 2.0 + PKCE, `/oauth/introspect`, MCP auth bypass | [`references/authentication.md`](skills/beeper-desktop-api/references/authentication.md) |
| HTTP status codes, error envelope shape, SDK exception mapping, retry guidance | [`references/errors.md`](skills/beeper-desktop-api/references/errors.md) |
| Remote access (Advanced Settings), `0.0.0.0` binding, `X-Forwarded-*` headers, Cloudflare Quick Tunnels + SSE caveat | [`references/remote-access.md`](skills/beeper-desktop-api/references/remote-access.md) |
| `bbctl` (Beeper Bridge Manager) overview and official bridge identifier list | [`references/bridges-self-hosting.md`](skills/beeper-desktop-api/references/bridges-self-hosting.md) |
| 11 end-to-end recipes: bulk DM, export chat to CSV, image attachment and poll sends, watch a chat via WebSocket, daily unread digest, etc. | [`references/cookbook.md`](skills/beeper-desktop-api/references/cookbook.md) |

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
    ├── beeper-desktop-api/
    │   ├── SKILL.md             # frontmatter + entry doc (the knowledge base)
    │   ├── references/          # progressive-disclosure reference library
    │       ├── endpoints-rest.md
    │       ├── sdk-typescript.md
    │       ├── sdk-python.md
    │       ├── sdk-go.md
    │       ├── schemas.md
    │       ├── websocket.md
    │       ├── mcp-server.md
    │       ├── authentication.md
    │       ├── polls.md
    │       ├── errors.md
    │       ├── remote-access.md
    │       ├── bridges-self-hosting.md
    │       └── cookbook.md
    │   └── scripts/
    │       └── send_poll.py        # experimental, dry-run-first poll helper
    └── beeper-messaging-manager/
        ├── SKILL.md             # orchestration + supervision + install guide
        ├── scripts/
        │   ├── install.py       # one-command, host-aware installer
        │   └── test_matches.py  # re-runnable alert-logic unit test
        └── templates/
            ├── watcher.py               # realtime WS alert daemon
            ├── digest.sh                # ranked-unread collector
            ├── digest_prompt.md         # reasoning prompt for the scheduled run
            ├── vip.json                 # editable alert-tuning config
            ├── alert.env                # delivery creds (Telegram / ALERT_CMD)
            ├── beeper-watcher.service   # systemd --user unit (Linux)
            └── com.beeper.watcher.plist # launchd agent (macOS)
```

`SKILL.md` is the only file the `skills` CLI strictly requires. The `references/` files are loaded on demand by the agent whenever it needs deep detail on a specific area — the progressive-disclosure pattern keeps context lean.

## Security

- Treat your `BEEPER_ACCESS_TOKEN` like an account credential. Anyone holding it can read and send messages on every network connected to your Beeper client.
- Prefer per-client OAuth tokens (revocable individually under **Settings → Developers → Approved connections**) over sharing a single long-lived token.
- The `beeper-desktop-api` skill includes an experimental `send_poll.py` helper. It is dry-run-only unless `--send` is supplied and reads Beeper's local Matrix session only with explicit `--allow-local-session`; review it before use. The `beeper-messaging-manager` skill also ships runnable scripts (`install.py`, `watcher.py`, `digest.sh`) — review them before running; its installer supports `--dry-run` to preview every action with zero side effects.

## Requirements for the installer

`beeper-messaging-manager/scripts/install.py` needs **Python 3.11+** with the
`venv` and `pip` modules (on Debian/Ubuntu: `sudo apt install python3.12
python3.12-venv`), plus the `beeper` CLI and `jq`. Invoke it with `python3` (or
a versioned `python3.12`) — bare `python` may resolve to an unsupported
interpreter. The installer version-gates itself and prints exact per-OS install
commands if the interpreter is too old or missing modules — it will not crash
with a bare traceback.

## License

[MIT](LICENSE).

## Not affiliated with Beeper

This is an unofficial, community-maintained skill. It documents Beeper's public Desktop API based on the official developer docs at https://developers.beeper.com/ but is not endorsed by or affiliated with Beeper / Automattic.

## Author

Maintained by **Avital Ben-Natan** ([@dewdad](https://github.com/dewdad)).

Builds on the upstream `beeper-desktop-api` skill by Gabe Fletcher; the
`beeper-messaging-manager` skill (installer + standing automations) is added
here.
