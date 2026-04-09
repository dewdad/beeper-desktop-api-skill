---
name: beeper-desktop-api
description: Complete reference for the Beeper Desktop API — a local HTTP + WebSocket + MCP server exposed by Beeper Desktop that lets code read, search, send, edit, react to, and stream messages across WhatsApp, iMessage, Telegram, Signal, Twitter/X, Discord, and every other network connected to the Beeper client. Use this skill whenever the user asks to build against the Beeper Desktop API, wire up the Beeper MCP server, send or search messages across chat networks through Beeper, automate Beeper Desktop, use @beeper/desktop-api (TS), beeper_desktop_api (Python), or github.com/beeper/desktop-api-go, subscribe to realtime message events via ws://localhost:23373/v1/ws, upload/download attachments via the Beeper assets endpoints, or integrate Beeper into an agent/script.
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
3. In **Settings → Developers → Approved connections**, click **+** to create an access token. Save it — you will need it for every request.

Environment variable convention used by the SDKs: `BEEPER_ACCESS_TOKEN`.

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

## SDKs

| Language | Package | Install |
|---|---|---|
| TypeScript | `@beeper/desktop-api` | `npm install @beeper/desktop-api` |
| Python | `beeper_desktop_api` | `pip install git+ssh://git@github.com/beeper/desktop-api-python.git` |
| Go | `github.com/beeper/desktop-api-go` | `go get github.com/beeper/desktop-api-go` |
| Terraform / Ruby / Java / Kotlin | Listed in docs | — |

For complete SDK method maps (every method, every param, every response shape), load:

- `references/sdk-typescript.md` — TS SDK (`@beeper/desktop-api`)
- `references/sdk-python.md` — Python SDK (sync + async)
- `references/sdk-go.md` — Go SDK

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

**Full parameter, request body, and response schemas for every endpoint are in `references/endpoints-rest.md`. Always load that file before writing code against a specific endpoint.**

## Realtime events (WebSocket, experimental)

Connect to `ws://localhost:23373/v1/ws` with `Authorization: Bearer <token>`, send a `subscriptions.set` command, and receive `chat.upserted` / `chat.deleted` / `message.upserted` / `message.deleted` events. Full protocol + schemas in `references/websocket.md`.

## MCP server

Beeper Desktop ships a built-in MCP server so agents (Claude Code, Cursor, VS Code, Windsurf, Gemini CLI) can search and send messages via MCP tools. Full setup by client in `references/mcp-server.md`.

Quick add for Claude Code:

```bash
claude mcp add beeper http://localhost:23373/v0/mcp -t http -s user
```

## Reference files

Load the relevant file for the task at hand:

- **`references/endpoints-rest.md`** — every REST endpoint with full request/response schemas, path/query/body params, and curl examples. Load this whenever writing direct HTTP calls or needing exhaustive param detail.
- **`references/sdk-typescript.md`** — `@beeper/desktop-api` complete method map, types, options, pagination, error classes.
- **`references/sdk-python.md`** — `beeper_desktop_api` sync and async clients, every namespace/method.
- **`references/sdk-go.md`** — `github.com/beeper/desktop-api-go` complete method map.
- **`references/schemas.md`** — shared object types (Account, Chat, Message, Attachment, Reaction, Participant) used everywhere in responses.
- **`references/websocket.md`** — experimental WebSocket realtime event protocol.
- **`references/mcp-server.md`** — MCP server setup for every client (Claude Desktop, Claude Code, Cursor, VS Code, Raycast, Windsurf, Warp, Codex, Gemini CLI) plus stdio proxy via `@beeper/mcp-remote`.
- **`references/remote-access.md`** — exposing the API to other machines: Advanced Settings toggle, `0.0.0.0` binding, `X-Forwarded-Host` / `X-Forwarded-Proto` base-URL derivation, Cloudflare Quick Tunnels setup, and the SSE-over-Cloudflare limitation.
- **`references/bridges-self-hosting.md`** — `bbctl` (Beeper Bridge Manager) overview, install/login/run, official bridge identifiers (telegram, whatsapp, signal, discord, slack, gmessages, meta, twitter, bluesky, imessage, linkedin, irc, …), and how self-hosted bridges surface through the Desktop API.
- **`references/authentication.md`** — in-app vs OAuth, introspection, MCP auth bypass, CORS notes.
- **`references/errors.md`** — status codes and error response shape.
- **`references/cookbook.md`** — common recipes (bulk DM, watch a chat, scrape messages to CSV, etc.).

## Out of scope (other Beeper developer surfaces)

developers.beeper.com also documents two adjacent surfaces that are NOT part of the Desktop API and therefore not covered by this skill beyond a brief mention here:

- **Android Content Providers** — `content://com.beeper.api/{chats,messages,contacts}` exposed by Beeper Android under permissions `com.beeper.android.permission.READ_PERMISSION` / `SEND_PERMISSION`. Separate API with its own columns, parameters, and change-notification model. Use the official Android docs when building against this.
- **Android Intents** — e.g. `com.beeper.android.TOGGLE_INCOGNITO_MODE` broadcast (requires Beeper Android ≥ 4.31.1 and a Plus subscription). Android-only.

## Guardrails

- **Never use `/v0/*`.** It is deprecated; use `/v1/*`. `/v0` is preserved only for the MCP endpoint path (`/v0/mcp`, `/v0/sse`).
- **Use `accountID`, not `network`**, for any write action. `network` is a display label and changes.
- **Download asset URLs promptly.** `srcURL` and avatar URLs may be temporary or local-only to the device.
- **Edits are text-only.** `PUT /v1/chats/{chatID}/messages/{messageID}` fails on messages with attachments.
- **Rate limits return 429.** Back off on 429 and retry with jitter; the SDKs do this automatically when `maxRetries > 0`.
- **iMessage quirk.** iMessage chats may not expose a stable `chatID` — the `get chat` endpoint warns about this. Use `localChatID` where available.
- **Cursor opacity.** Never inspect or mutate cursor strings. Pass them back verbatim with `direction`.
- **Search is literal.** `query=` does literal word matching — NOT semantic search. All words must match.
