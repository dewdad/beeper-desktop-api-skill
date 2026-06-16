---
name: beeper-desktop-api
description: |
  Local HTTP + WebSocket + MCP server exposed by Beeper Desktop for reading,
  searching, sending, editing, reacting to, and streaming messages across
  WhatsApp, iMessage, Telegram, Signal, Twitter/X, Discord, and every other
  network connected to the Beeper client. Use when the user asks to build
  against the Beeper Desktop API; wire up the Beeper MCP server; send or
  search messages across chat networks through Beeper; automate Beeper
  Desktop; use the official `beeper` CLI / `@beeper/cli` (e.g. `beeper
  messages`, `beeper chats`, `beeper send`, `beeper targets`, `beeper watch`,
  `beeper rpc`); use the `@beeper/desktop-api`, `beeper_desktop_api`, or
  `desktop-api-go` SDKs; subscribe to realtime events via
  `ws://localhost:23373/v1/ws`; upload/download attachments via the assets
  endpoints; launch Beeper Desktop programmatically; or point a CLI / SDK
  at a running Beeper Desktop or managed Beeper Server target.
license: MIT
compatibility: |
  Requires Beeper Desktop ≥ 4.1.169 with Settings → Developers → Beeper
  Desktop API enabled. References cover the official `@beeper/cli`, the
  `@beeper/desktop-api` (TS), `beeper_desktop_api` (Python), and
  `github.com/beeper/desktop-api-go` SDKs, plus the experimental WebSocket
  event stream and the built-in MCP server.
metadata:
  version: "1.1.0"
  upstream: https://github.com/gfsaaser24/beeper-desktop-api-skill
  changelog: |
    1.1.0 — Add references/cli.md (Beeper CLI reference + Desktop-target
            runbook + programmatic launch). Convert reference list to real
            markdown links, add TOCs to large references, and fold license /
            compatibility / version metadata into frontmatter.
    1.0.0 — Initial port of the upstream skill.
---

# Beeper Desktop API

## Overview

Beeper Desktop ships a local REST + WebSocket + MCP server that lets code interact with every chat network the user has connected — WhatsApp, iMessage, Signal, Telegram, Twitter/X, Discord, Matrix, Instagram, LinkedIn, etc. — through a single unified surface.

**Default server:** `http://localhost:23373`
**WebSocket:** `ws://localhost:23373/v1/ws`
**MCP (HTTP stream):** `http://localhost:23373/v0/mcp`
**MCP (SSE):** `http://localhost:23373/v0/sse`
**Minimum Beeper Desktop version:** 4.1.169+

## Prerequisites

1. Install Beeper Desktop from https://www.beeper.com/download (v4.1.169 or newer).
2. Open Beeper, go to **Settings → Developers → Beeper Desktop API**, and enable the server.
3. In **Settings → Developers → Approved connections**, click **+** to create an access token. Save it — every request needs it as a bearer token.

Environment variable convention used by the SDKs: `BEEPER_ACCESS_TOKEN`.

## Pre-flight (run this FIRST when CLI/SDK returns empty data)

The single most common failure mode: **silent empty results from a not-yet-ready target**. The CLI/SDK happily returns `{ success: true, data: [] }` when pointed at a target whose `readiness.state != "ready"`. This looks like "the user has no chats" but is actually "wrong target".

```bash
beeper targets list --json     # see all reachable targets
beeper status --json           # readiness of the DEFAULT target
```

A workstation may have BOTH targets running:

| Target | Default port | Typical role |
|---|---|---|
| `desktop` | `:23373` | Beeper Desktop app — the user's actual signed-in client |
| `beeper-server` | `:23374` | CLI-managed headless Beeper Server, often `state: "initializing"` |

If `beeper status --json` shows `readiness.state` other than `ready` (e.g. `initializing`, `setup`), **the default target is not usable**. Pass `--target desktop` (or whichever IS ready) explicitly to every subsequent command, e.g.:

```bash
beeper chats list --target desktop --account whatsapp --limit 10 --json
```

**Rule of thumb:** an empty `data: []` from `chats list` / `messages list` on an account whose `status` is `connected` is almost always a target/readiness issue, not an empty inbox. Re-run with `--target desktop` before assuming anything else.

The same applies to SDK clients: construct `BeeperDesktop({ baseURL: 'http://127.0.0.1:23373' })` to talk to the desktop app instead of the (possibly-initializing) default server on `:23374`.

## Common tasks (start here before reading endpoint reference)

| Task | Command |
|---|---|
| What did I miss on WhatsApp? (top recent chats) | `beeper chats list --target desktop --account whatsapp --limit 10 --json` |
| Only chats that matter (unread, not muted, not low-priority) | `beeper chats list --target desktop --unread --no-muted --no-low-priority --json` |
| Last N messages in one chat | `beeper messages list --target desktop --chat '<chatID>' --limit N --json` |
| Search across all networks | `beeper messages search "<query>" --limit 20 --json` |
| Realtime stream of new messages/chats | `beeper watch --target desktop --json` |
| Send a text message | `beeper send text --target desktop --to '<chatID|title|search>' --message "Hi" --wait` |
| Raw HTTP escape hatch | `beeper api get /v1/info --target desktop` |

> ⚠️ `beeper send` is a command **group**, not a verb. Use `beeper send text` / `send file` / `send react` / `send sticker` / `send voice`. The text variant requires `--to` and `--message` flags (no positional args). `--to` accepts a chatID, numeric local chat ID, exact title, or fuzzy search text; pair with `--pick N` to disambiguate. Add `--wait` to block until Desktop confirms the send (or it fails).

There is **no** `beeper inbox` command. To build an "inbox view", combine `chats list --unread --no-muted` with a per-chat `messages list --limit N` loop:

```bash
beeper chats list --target desktop --unread --no-muted --no-low-priority --limit 10 --json \
  | jq -r '.data[].id' \
  | while read -r chat; do
      echo "=== $chat ==="
      beeper messages list --target desktop --chat "$chat" --limit 3 --json \
        | jq -r '.data[] | "  [\(.timestamp)] \(.senderName // .senderID): \(.text // "<no text>")"'
    done
```

### Field & content gotchas

- **Message text may contain HTML.** WhatsApp news/broadcast channels (and some Matrix bridges) deliver messages with `<strong>`, `<br>`, `<a href="...">`, and HTML entities (`&gt;`, `&amp;`). Strip with `bleach`, `html2text`, or a simple regex before plaintext display.
- **`senderName` is optional.** Always fall back to `senderID` (e.g. `m.senderName or m.senderID` / `m.senderName ?? m.senderID`). Bridge bots like `@whatsappbot:beeper.local` often appear as the sender for broadcast channels.
- **`chatID` may be missing on iMessage.** Use `localChatID` when present.
- **Chat sort order.** `chats list` returns chats sorted by `lastActivity` descending — first item is the most recently active.
- **Filter flags exist for noise reduction** (often missed): `--unread`, `--no-muted`, `--no-low-priority`, `--no-archived`, `--pinned`, `--account <id|network|bridge>`. Combine them.

## Authentication

All endpoints (REST, WebSocket, and MCP) accept a standard bearer token:

```
Authorization: Bearer <your_token>
```

Token acquisition modes:

- **In-app** — Settings → Developers → Approved connections → **+**.
- **OAuth 2.0 (PKCE)** — Discovery metadata at `GET /.well-known/oauth-authorization-server` (RFC 8414). The built-in MCP server handles OAuth automatically per the MCP authorization spec. Most clients (Claude Code, Cursor, VS Code, Windsurf, Gemini CLI) go through OAuth automatically when connecting to the HTTP-streamable MCP endpoint.
- **Token introspection** — `POST /oauth/introspect` with `Content-Type: application/x-www-form-urlencoded` body `token=<token>&token_type_hint=access_token`. Returns `{ active: true, ... }` or `{ active: false }`.

When a bearer token is passed to the MCP endpoints (`/v0/mcp`, `/v0/sse`), OAuth is bypassed and the token is used directly.

## Key concepts

- **accountID** — stable ID for a connected network (e.g. `local-whatsapp_ba_EvYDBBsZbRQAy3UOSWqG0LuTVkc`). **Always use `accountID`** for routing actions. `network` (`"WhatsApp"`, `"Telegram"`, ...) is display-only.
- **chatID** — room/thread identifier, often in Matrix format (`!NCdzlIaMjZUmvmvyHU:beeper.com`). Some chats (notably iMessage) don't have durable IDs — use `localChatID` when surfaced.
- **messageID** — stable per-message ID, suitable for cursor-based pagination and editing/reacting.
- **Pagination model** — cursor-based. Responses return `oldestCursor` / `newestCursor` + `hasMore`. To fetch the next page, pass the appropriate cursor plus `direction=before` (older) or `direction=after` (newer). The TS/Python/Go SDKs hide this behind async iterators.
- **Attachments** — upload first to `/v1/assets/upload` (multipart) or `/v1/assets/upload/base64`, get back an `uploadID`, then reference that `uploadID` in the `attachment` field of `POST /v1/chats/{chatID}/messages`.
- **Asset URLs** — `mxc://...` (remote Matrix content), `localmxc://...` (local Beeper content), or `file://...`. Download via `POST /v1/assets/download` or stream directly via `GET /v1/assets/serve?url=...` (supports HTTP Range).
- **Editing** — text-only. Messages with attachments cannot be edited.
- **Versioning** — `/v1/*` is the current RESTful surface. `/v0/*` is gRPC-style and deprecated (breaking change in Beeper Desktop 4.1.294, 2025-10-16). Always prefer `/v1`.

## CLI (`@beeper/cli`)

The official `beeper` command-line tool is the cheapest, fastest path for shell-level automation, agents, and ad-hoc scripts on a workstation that already has Beeper Desktop installed and signed in. It wraps every endpoint listed below, returns `--json` envelopes, and supports multiple **targets** (a running Beeper Desktop on `:23373`, a CLI-managed Beeper Server on `:23374`, or a remote URL).

```bash
npm install -g @beeper/cli
beeper status                                      # readiness + endpoint
beeper accounts list --json                         # connected networks
beeper messages search "invoice" --account whatsapp --limit 20 --json
beeper send "Hi" --chat <selector>
beeper watch --json                                 # realtime NDJSON stream
beeper api get /v1/info                             # raw HTTP escape hatch
```

For the full command surface, the **runbook for pointing the CLI at a running Beeper Desktop** (including the `dataDir` fix, the manual `bdapi_*` token flow, and how to launch Desktop programmatically when it isn't running), known broken paths, and recipes — load [references/cli.md](references/cli.md). Whenever the user mentions `beeper` (the CLI), `beeper-cli`, `@beeper/cli`, or any `beeper <subcommand>`, that file is the canonical answer.

## SDKs

| Language | Package | Install |
|---|---|---|
| TypeScript | `@beeper/desktop-api` | `npm install @beeper/desktop-api` |
| Python | `beeper_desktop_api` | `pip install git+ssh://git@github.com/beeper/desktop-api-python.git` |
| Go | `github.com/beeper/desktop-api-go` | `go get github.com/beeper/desktop-api-go` |
| Terraform / Ruby / Java / Kotlin | Listed in docs | — |

For complete SDK method maps (every method, every param, every response shape), load:

- [references/sdk-typescript.md](references/sdk-typescript.md) — TS SDK (`@beeper/desktop-api`)
- [references/sdk-python.md](references/sdk-python.md) — Python SDK (sync + async)
- [references/sdk-go.md](references/sdk-go.md) — Go SDK

## Quick start

### curl

```bash
export BEEPER_ACCESS_TOKEN="your_token_here"

# 1. Verify the server is up and discover endpoints
curl http://localhost:23373/v1/info \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"

# 2. List connected networks
curl http://localhost:23373/v1/accounts \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"

# 3. List chats (paginated)
curl http://localhost:23373/v1/chats \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"

# 4. Send a message
curl -X POST http://localhost:23373/v1/chats/$CHAT_ID/messages \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from curl"}'
```

### TypeScript

```ts
import BeeperDesktop from '@beeper/desktop-api';

const client = new BeeperDesktop({ accessToken: process.env.BEEPER_ACCESS_TOKEN });

const info = await client.info.retrieve();
const accounts = await client.accounts.list();

// Auto-paginate messages matching a query
for await (const msg of client.messages.search({ query: 'invoice', limit: 50 })) {
  console.log(msg.senderName, msg.text);
}

// Send a reply
await client.messages.send(chatID, { text: 'On it', replyToMessageID: msgID });
```

### Python

```python
from beeper_desktop_api import BeeperDesktop

client = BeeperDesktop()  # reads BEEPER_ACCESS_TOKEN from env

info = client.info.retrieve()
for account in client.accounts.list():
    print(account.network, account.account_id)

for msg in client.messages.search(query="invoice", limit=50):
    print(msg.sender_name, msg.text)

client.messages.send(chat_id, body={"text": "On it", "reply_to_message_id": msg_id})
```

### Go

```go
import (
    "context"
    beeperdesktopapi "github.com/beeper/desktop-api-go"
    "github.com/beeper/desktop-api-go/option"
)

client := beeperdesktopapi.NewClient(
    option.WithAccessToken(os.Getenv("BEEPER_ACCESS_TOKEN")),
)

info, _ := client.Info.Get(context.TODO())
accounts, _ := client.Accounts.List(context.TODO())
```

## REST endpoint summary

| Area | Method | Path | Summary |
|---|---|---|---|
| Server | GET | `/v1/info` | Discovery: app/platform/server/endpoints metadata |
| Accounts | GET | `/v1/accounts` | List connected networks |
| Chats | GET | `/v1/chats` | List chats (paginated, sorted by last activity) |
| Chats | POST | `/v1/chats` | Create (`mode=create`) or start (`mode=start`) a chat |
| Chats | GET | `/v1/chats/{chatID}` | Retrieve chat details |
| Chats | GET | `/v1/chats/search` | Search chats by title/participants |
| Chats | POST | `/v1/chats/{chatID}/archive` | Archive / unarchive |
| Reminders | POST | `/v1/chats/{chatID}/reminders` | Create chat reminder |
| Reminders | DELETE | `/v1/chats/{chatID}/reminders` | Clear chat reminder |
| Messages | GET | `/v1/chats/{chatID}/messages` | List messages (cursor pagination) |
| Messages | POST | `/v1/chats/{chatID}/messages` | Send message (text, attachment, reply) |
| Messages | PUT | `/v1/chats/{chatID}/messages/{messageID}` | Edit message text |
| Reactions | POST | `/v1/chats/{chatID}/messages/{messageID}/reactions` | Add reaction |
| Reactions | DELETE | `/v1/chats/{chatID}/messages/{messageID}/reactions` | Remove reaction |
| Messages | GET | `/v1/messages/search` | Cross-chat message search with filters |
| Contacts | GET | `/v1/accounts/{accountID}/contacts` | Search contacts on one account |
| Contacts | GET | `/v1/accounts/{accountID}/contacts/list` | Paginated contact list |
| Search | GET | `/v1/search` | Unified search (chats + participants + first page of messages) |
| Assets | GET | `/v1/assets/serve?url=` | Stream asset (Range-supported) |
| Assets | POST | `/v1/assets/download` | Download mxc/localmxc to local file URL |
| Assets | POST | `/v1/assets/upload` | Upload via multipart/form-data |
| Assets | POST | `/v1/assets/upload/base64` | Upload via JSON base64 |
| App | POST | `/v1/focus` | Focus Beeper Desktop window, optionally open chat/message/draft |
| OAuth | GET | `/.well-known/oauth-authorization-server` | OAuth 2.0 discovery |
| OAuth | POST | `/oauth/introspect` | Token introspection |

**Full parameter, request body, and response schemas for every endpoint are in [references/endpoints-rest.md](references/endpoints-rest.md). Always load that file before writing code against a specific endpoint.**

## Realtime events (WebSocket, experimental)

Connect to `ws://localhost:23373/v1/ws` with `Authorization: Bearer <token>`, send a `subscriptions.set` command, and receive `chat.upserted` / `chat.deleted` / `message.upserted` / `message.deleted` events. Full protocol + schemas in [references/websocket.md](references/websocket.md).

## MCP server

Beeper Desktop ships a built-in MCP server so agents (Claude Code, Cursor, VS Code, Windsurf, Gemini CLI) can search and send messages via MCP tools. Full setup by client in [references/mcp-server.md](references/mcp-server.md).

Quick add for Claude Code:

```bash
claude mcp add beeper http://localhost:23373/v0/mcp -t http -s user
```

## Reference files

Load the relevant file for the task at hand:

- [references/cli.md](references/cli.md) — `@beeper/cli` (`beeper`) reference: targets model, auth resolution, full command surface, runbook for pointing the CLI at a running Beeper Desktop (with the Linux `dataDir` fix, the manual `bdapi_*` token flow, and how to launch Desktop programmatically), known broken paths, recipes. Load this whenever the user is using or asking about the `beeper` CLI.
- [references/endpoints-rest.md](references/endpoints-rest.md) — every REST endpoint with full request/response schemas, path/query/body params, and curl examples. Load this whenever writing direct HTTP calls or needing exhaustive param detail.
- [references/sdk-typescript.md](references/sdk-typescript.md) — `@beeper/desktop-api` complete method map, types, options, pagination, error classes.
- [references/sdk-python.md](references/sdk-python.md) — `beeper_desktop_api` sync and async clients, every namespace/method.
- [references/sdk-go.md](references/sdk-go.md) — `github.com/beeper/desktop-api-go` complete method map.
- [references/schemas.md](references/schemas.md) — shared object types (Account, Chat, Message, Attachment, Reaction, Participant) used everywhere in responses.
- [references/websocket.md](references/websocket.md) — experimental WebSocket realtime event protocol.
- [references/mcp-server.md](references/mcp-server.md) — MCP server setup for every client (Claude Desktop, Claude Code, Cursor, VS Code, Raycast, Windsurf, Warp, Codex, Gemini CLI) plus stdio proxy via `@beeper/mcp-remote`.
- [references/remote-access.md](references/remote-access.md) — exposing the API to other machines: Advanced Settings toggle, `0.0.0.0` binding, `X-Forwarded-Host` / `X-Forwarded-Proto` base-URL derivation, Cloudflare Quick Tunnels setup, and the SSE-over-Cloudflare limitation.
- [references/bridges-self-hosting.md](references/bridges-self-hosting.md) — `bbctl` (Beeper Bridge Manager) overview, install/login/run, official bridge identifiers (telegram, whatsapp, signal, discord, slack, gmessages, meta, twitter, bluesky, imessage, linkedin, irc, …), and how self-hosted bridges surface through the Desktop API.
- [references/authentication.md](references/authentication.md) — in-app vs OAuth, introspection, MCP auth bypass, CORS notes.
- [references/errors.md](references/errors.md) — status codes and error response shape.
- [references/cookbook.md](references/cookbook.md) — common recipes (bulk DM, watch a chat, scrape messages to CSV, etc.).

## Out of scope (other Beeper developer surfaces)

developers.beeper.com also documents two adjacent surfaces that are NOT part of the Desktop API and therefore not covered by this skill beyond a brief mention here:

- **Android Content Providers** — `content://com.beeper.api/{chats,messages,contacts}` exposed by Beeper Android under permissions `com.beeper.android.permission.READ_PERMISSION` / `SEND_PERMISSION`. Separate API with its own columns, parameters, and change-notification model. Use the official Android docs when building against this.
- **Android Intents** — e.g. `com.beeper.android.TOGGLE_INCOGNITO_MODE` broadcast (requires Beeper Android ≥ 4.31.1 and a Plus subscription). Android-only.

## Guardrails

- **Empty `data: []` ≠ empty inbox.** When `chats list` / `messages list` returns no rows on a `connected` account, suspect a non-ready target FIRST. Run `beeper status --json`; if `readiness.state != "ready"`, retry with `--target desktop` (or whichever target IS ready). See the **Pre-flight** section.
- **Never use `/v0/*`.** It is deprecated; use `/v1/*`. `/v0` is preserved only for the MCP endpoint path (`/v0/mcp`, `/v0/sse`).
- **Treat `Message.text` as untrusted HTML.** WhatsApp news/broadcast bridges deliver HTML (`<strong>`, `<br>`, `<a>`) and entities (`&gt;`). Strip before plaintext display.
- **`senderName` is optional.** Always fall back to `senderID`.
- **`beeper send` is a command group.** Use `beeper send text --to <selector> --message <text>`, not `beeper send "..." --chat ...`. Same applies to `send file`, `send react`, `send sticker`, `send voice`.
- **Use `accountID`, not `network`**, for any write action. `network` is a display label and changes.
- **Download asset URLs promptly.** `srcURL` and avatar URLs may be temporary or local-only to the device.
- **Edits are text-only.** `PUT /v1/chats/{chatID}/messages/{messageID}` fails on messages with attachments.
- **Rate limits return 429.** Back off on 429 and retry with jitter; the SDKs do this automatically when `maxRetries > 0`.
- **iMessage quirk.** iMessage chats may not expose a stable `chatID` — the `get chat` endpoint warns about this. Use `localChatID` where available.
- **Cursor opacity.** Never inspect or mutate cursor strings. Pass them back verbatim with `direction`.
- **Search is literal.** `query=` does literal word matching — NOT semantic search. All words must match.
