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
  version: "1.2.0"
  upstream: https://github.com/gfsaaser24/beeper-desktop-api-skill
  changelog: |
    1.2.0 — Progressive disclosure: trimmed always-loaded SKILL.md from ~336
            to ~200 lines. Moved per-language Quick Start snippets, full REST
            endpoint table, deep Authentication, CLI overview, SDKs install
            table, and MCP setup into their existing references/*.md files
            (load on demand). Replaced the Reference files narrative with a
            decision table ("if you're doing X, load Y FIRST").
    1.1.0 — Add references/cli.md (Beeper CLI reference + Desktop-target
            runbook + programmatic launch). Convert reference list to real
            markdown links, add TOCs to large references, and fold license /
            compatibility / version metadata into frontmatter.
    1.0.0 — Initial port of the upstream skill.
---

# Beeper Desktop API

Local REST + WebSocket + MCP server exposed by Beeper Desktop. Lets code talk to every chat network the user has connected (WhatsApp, iMessage, Signal, Telegram, Twitter/X, Discord, Matrix, Instagram, LinkedIn, …) through one unified surface.

- **Default REST base:** `http://localhost:23373` (`/v1/*` is current; `/v0/*` is deprecated)
- **WebSocket:** `ws://localhost:23373/v1/ws`
- **MCP:** `http://localhost:23373/v0/mcp` (HTTP-stream) or `.../v0/sse`
- **Minimum Beeper Desktop version:** 4.1.169+

## Prerequisites

1. Install Beeper Desktop from https://www.beeper.com/download (v4.1.169 or newer).
2. Open Beeper, go to **Settings → Developers → Beeper Desktop API**, and enable the server.
3. In **Settings → Developers → Approved connections**, click **+** to create an access token.
4. Export it as `BEEPER_ACCESS_TOKEN` — every request needs it as a bearer token.

OAuth 2.0 (PKCE) and token introspection are also supported — see [references/authentication.md](references/authentication.md).

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

- **Message text may contain HTML.** WhatsApp news/broadcast channels AND Matrix bridges deliver messages with `<strong>`, `<br>`, `<a href="...">`, and HTML entities (`&gt;`, `&amp;`). Strip with `bleach`, `html2text`, or a simple regex before plaintext display.
- **`text` can be empty string or `null`.** Attachment-only messages (image/voice/file with no caption) have no text. Treat empty text as a valid non-error state.
- **`senderName` is optional.** Always fall back to `senderID` (e.g. `m.senderName or m.senderID` / `m.senderName ?? m.senderID`). Bridge bots like `@whatsappbot:beeper.local` often appear as the sender for broadcast channels.
- **`chatID` may be missing on iMessage.** Use `localChatID` when present.
- **Chat sort order.** `chats list` returns chats sorted by `lastActivity` descending — first item is the most recently active.
- **Filter flags exist for noise reduction** (often missed): `--unread`, `--no-muted`, `--no-low-priority`, `--no-archived`, `--pinned`, `--account <id|network|bridge>`. Combine them.
- **`messages list` returns event pseudo-messages.** Reactions appear as full message rows with `type: "REACTION"`, `text: null`, `isHidden: true`, and `linkedMessageID` pointing at the real message. **Filter `m.type === "TEXT"` (or check `!m.isHidden`) when iterating, or you'll mistake reactions for messages.** The same pattern likely applies to other event types (joins, kicks, pins).
- **`linkedMessageID` is overloaded by `type`:**
  - `type: "TEXT"` + `linkedMessageID` → this message is a **reply** to that ID
  - `type: "REACTION"` + `linkedMessageID` → this is a **reaction** to that ID
- **Naming asymmetry: reply field.** CLI flag is `--reply-to <msgID>`; SDK/REST request field is `replyToMessageID`; **response field is `linkedMessageID`** (not `replyToMessageID`). All three refer to the same thing.
- **Edit responses are stale.** `messages edit` / `PUT /v1/chats/{chatID}/messages/{messageID}` returns `success: true` plus the message in its **pre-edit** state. To confirm the new text, re-read via `messages show` / `messages list`. Edited messages gain an `editedTimestamp` field.
- **`sendStatus` is inconsistent across networks.** Present on Google Chat send responses; absent on Telegram/Matrix. Don't depend on it for delivery confirmation — use `--wait` (CLI) or poll `messages show` if you need certainty.
- **Search is literal CONTIGUOUS SUBSTRING**, not multi-word bag-of-words. `messages search "hello CLI"` will NOT match a message containing `"hello from CLI"` — only messages containing the exact substring `"hello CLI"`. To find messages with multiple terms, query each separately and intersect, or use the unique tokens that actually appear contiguously in your target text.

## Key concepts (routing essentials only)

- **`accountID`** — stable ID for a connected network (e.g. `local-whatsapp_ba_EvYDBBsZbRQAy3UOSWqG0LuTVkc`). **Always use `accountID`** for routing actions. `network` (`"WhatsApp"`, `"Telegram"`, …) is a display label and can change between releases.
- **`chatID`** — room/thread identifier, often Matrix-format (`!NCdzlIaMjZUmvmvyHU:beeper.com`). iMessage chats may not have a durable `chatID` — fall back to `localChatID`.
- **`messageID`** — stable per-message ID, suitable for cursor-based pagination and editing/reacting.
- **Pagination** — cursor-based. Responses return `oldestCursor` / `newestCursor` + `hasMore`. Pass cursors back verbatim with `direction=before` (older) or `direction=after` (newer). The TS/Python/Go SDKs hide this behind async iterators.
- **Attachments are a 2-step flow** — upload first to `/v1/assets/upload` (multipart) or `/v1/assets/upload/base64`, get back an `uploadID`, then reference that `uploadID` in the `attachment` field of `POST /v1/chats/{chatID}/messages`. Full schemas in [references/endpoints-rest.md](references/endpoints-rest.md).
- **Versioning** — `/v1/*` is the current RESTful surface. `/v0/*` is gRPC-style and deprecated (breaking change in Beeper Desktop 4.1.294, 2025-10-16). Always prefer `/v1`.

Detailed object shapes (`Account`, `Chat`, `Message`, `Attachment`, `Reaction`, `Participant`) → [references/schemas.md](references/schemas.md).

## When to load which reference

Decide what you're doing, load the matching file FIRST, then write code:

| If you're doing… | Load this reference FIRST |
|---|---|
| Anything with the `beeper` CLI (commands, targets, runbook for pointing at running Desktop, programmatic launch, broken paths) | [references/cli.md](references/cli.md) |
| Writing TypeScript / JavaScript / Node / Deno / Bun code | [references/sdk-typescript.md](references/sdk-typescript.md) |
| Writing Python (sync or async) | [references/sdk-python.md](references/sdk-python.md) |
| Writing Go | [references/sdk-go.md](references/sdk-go.md) |
| Writing direct HTTP / curl, or need exhaustive request/response schemas | [references/endpoints-rest.md](references/endpoints-rest.md) |
| Setting up the MCP server in any agent client (Claude Desktop, Claude Code, Cursor, VS Code, Raycast, Windsurf, Warp, Codex, Gemini CLI, stdio bridges) | [references/mcp-server.md](references/mcp-server.md) |
| Subscribing to realtime events (`chat.upserted`, `message.upserted`, …) | [references/websocket.md](references/websocket.md) |
| OAuth 2.0 / PKCE / token introspection / MCP auth bypass / CORS | [references/authentication.md](references/authentication.md) |
| Status codes, error envelope shape, retry semantics | [references/errors.md](references/errors.md) |
| Calling the API from another machine (`0.0.0.0` binding, Cloudflare Tunnel, SSE caveats) | [references/remote-access.md](references/remote-access.md) |
| Self-hosting bridges (`bbctl` / Beeper Bridge Manager, official bridge IDs) | [references/bridges-self-hosting.md](references/bridges-self-hosting.md) |
| Recipe-shaped tasks (bulk DM, scrape to CSV, watch a chat, …) | [references/cookbook.md](references/cookbook.md) |
| Decoding response field shapes (`Message`, `Chat`, `Account`, `Attachment`, …) | [references/schemas.md](references/schemas.md) |

> **Default path on a workstation that already has Beeper Desktop signed in:** start with the CLI ([references/cli.md](references/cli.md)). It needs no SDK install, no token plumbing, and emits `--json` envelopes. Only drop down to an SDK or raw HTTP when the CLI doesn't expose the needed surface or you're embedding into a long-running process.

## Out of scope

Beeper publishes two unrelated developer surfaces that this skill does NOT cover: **Android Content Providers** (`content://com.beeper.api/...`) and **Android Intents** (e.g. `com.beeper.android.TOGGLE_INCOGNITO_MODE`). Use the official Android docs for those.

## Guardrails

- **Empty `data: []` ≠ empty inbox.** When `chats list` / `messages list` returns no rows on a `connected` account, suspect a non-ready target FIRST. Run `beeper status --json`; if `readiness.state != "ready"`, retry with `--target desktop` (or whichever target IS ready). See the **Pre-flight** section.
- **Never use `/v0/*`.** It is deprecated; use `/v1/*`. `/v0` is preserved only for the MCP endpoint path (`/v0/mcp`, `/v0/sse`).
- **Treat `Message.text` as untrusted HTML.** WhatsApp news/broadcast bridges deliver HTML (`<strong>`, `<br>`, `<a>`) and entities (`&gt;`). Strip before plaintext display.
- **`senderName` is optional.** Always fall back to `senderID`.
- **`beeper send` is a command group.** Use `beeper send text --to <selector> --message <text>`, not `beeper send "..." --chat ...`. Same applies to `send file`, `send react`, `send sticker`, `send voice`.
- **Use `accountID`, not `network`**, for any write action. `network` is a display label and changes.
- **Download asset URLs promptly.** `srcURL` and avatar URLs (`mxc://`, `localmxc://`, `file://`) may be temporary or local-only to the device. Resolve via `assets.serve` / `assets.download`.
- **Edits are text-only.** `PUT /v1/chats/{chatID}/messages/{messageID}` fails on messages with attachments.
- **Rate limits return 429.** Back off on 429 and retry with jitter; the SDKs do this automatically when `maxRetries > 0`.
- **iMessage quirk.** iMessage chats may not expose a stable `chatID`. Use `localChatID` where available.
- **Cursor opacity.** Never inspect or mutate cursor strings. Pass them back verbatim with `direction`.
- **Search is literal CONTIGUOUS SUBSTRING.** `messages search "foo bar"` matches only messages containing the exact substring `"foo bar"`, NOT "messages containing both foo and bar somewhere". Not semantic, not bag-of-words. Use unique tokens that actually appear next to each other in your target text.
- **`messages list` includes pseudo-messages.** Reactions (and likely other events) come back as rows with `type !== "TEXT"` and `isHidden: true`. Filter them out when treating the result as a message stream.
- **Edit responses are stale.** The response from a successful edit returns the message in its **pre-edit** state. Re-read to confirm the new text; check `editedTimestamp` to detect edits.
- **`linkedMessageID` is overloaded** — it's the reply parent for `type: "TEXT"` and the reaction target for `type: "REACTION"`. Always disambiguate by `type`.
