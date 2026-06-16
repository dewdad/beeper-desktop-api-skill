# `@beeper/cli` — official Beeper CLI

The Beeper team ships a first-class command-line tool that wraps the Desktop API. For an agent on a workstation that already has Beeper Desktop installed and signed in, **the CLI is usually the cheapest, fastest path** — no SDK install, no token plumbing inside your script, JSON envelopes on every command.

This file documents:

1. Install + mental model (targets, auth, JSON output).
2. The full command surface — what's available, when to use which.
3. The **runbook for pointing the CLI at a running Beeper Desktop** (and the Linux/auto-auth gotchas you'll hit).
4. Failure modes and how to recognize them.

> Treat this file as the canonical CLI reference for this skill. Load it whenever the user mentions `beeper` (the CLI), `beeper-cli`, `@beeper/cli`, "the Beeper CLI", `beeper messages`, `beeper chats`, `beeper send`, `beeper api`, `beeper targets`, `beeper status`, `beeper rpc`, etc., **or** asks how to talk to Beeper from a shell / agent / script.

---

## Install

```bash
npm install -g @beeper/cli         # provides the `beeper` binary
beeper version                     # confirm installed
```

The CLI auto-downloads a pinned binary on first run into `~/.cache/beeper-cli/binary/<hash>/`.

Local data lives under `~/.beeper/`:

```
~/.beeper/
  config.json            # global { defaultTarget }
  cache.json             # last-known target state (no secrets)
  targets/<name>.json    # one file per target — { baseURL, type, auth, runtime, dataDir, ... }
  profiles/...           # data dirs for managed installs (CLI-spawned servers/desktops)
  installations.json     # tracks managed runtime versions
```

---

## Mental model: targets

Every `beeper` invocation runs against **one target**. A target is a `(baseURL, auth, type)` triple stored in `~/.beeper/targets/<name>.json`.

Three target *types*:

| Type | What it talks to | Created by |
|---|---|---|
| `desktop` | A running Beeper Desktop's API on `127.0.0.1:23373` | `beeper targets add desktop` (existing app) — or auto-launched managed Desktop |
| `server` | A headless **Beeper Server** managed by the CLI on `127.0.0.1:23374` | `beeper targets add server` / `beeper setup --server` |
| `remote` | Any reachable Beeper Desktop / Server URL | `beeper targets add remote --url ...` |

Select the active target three ways (highest precedence first):

1. `--target <name>` flag on any command.
2. `--base-url <url>` flag (becomes an unnamed `custom` target for that call).
3. `defaultTarget` in `~/.beeper/config.json` (set with `beeper targets use <name>`).

Inspect: `beeper targets`, `beeper targets show --target <name>`, `beeper status [--target <name>]`.

---

## Mental model: auth

Token resolution order on every command:

1. `BEEPER_ACCESS_TOKEN` env var (overrides everything).
2. `target.auth.accessToken` in `~/.beeper/targets/<name>.json`.
3. `config.auth.accessToken` in `~/.beeper/config.json` (legacy fallback).

Inspect with `beeper auth status [--target <name>]`. Clear with `beeper auth logout`.

Token *kinds* the Desktop API accepts:

- **`bdapi_*`** — long-lived bearer tokens minted via **Settings → Developers → Approved connections → +**. The supported, durable path.
- **OAuth-issued tokens** — created via `/oauth/register` + `/oauth/authorize` (PKCE). The CLI tries this with `beeper setup --oauth`, but as of CLI 0.6.x this often returns `server_error` and is unreliable.
- **NOT** the Matrix `syt_*` access token from `index.db → beeperState.access_token`. The CLI's `--local` shortcut reads exactly that token, which results in `401 Invalid or missing token` from `/v1/*`. **Treat `beeper setup --target desktop --local` as broken for the data API** until upstream fixes it.

---

## Universal flags worth knowing

| Flag | Effect |
|---|---|
| `--json` | Print machine-readable `{ success, data, error, exitCode, kind }` envelope on stdout. Use this from scripts. |
| `--quiet` (`-q`) | Suppress spinners / success banners. |
| `--full` | Disable text truncation; print full IDs and message bodies. Set this whenever piping to `jq` / `python -c`. |
| `--ids` | Print only IDs (chats, messages, contacts) — handy for shell pipelines. |
| `--target <name>` / `-t <name>` | Pick which target to run against. |
| `--base-url <url>` | One-shot custom target. |
| `--read-only` (or `BEEPER_READONLY=1`) | Reject any command that would mutate state. Recommended for read-only agents. |
| `--debug` | SDK-level HTTP logging on stderr. |
| `--events` | NDJSON lifecycle events on stderr (long-running commands). |
| `--timeout 30s` | Cap any command (suffixes: `s`, `m`, `h`). |

JSON envelope on every command:

```json
{ "success": true, "data": <payload>, "error": null, "exitCode": 0 }
```

On failure: `{"success": false, "data": null, "error": "500 Failed to execute tool: getChat", "exitCode": 1, "kind": "bug"}`. Always check `success` and `data != null` before consuming `data`.

---

## Command surface (read-most-of-the-API)

```text
beeper targets         # add / list / show / use / start / stop / restart / logs / status
beeper setup           # bring a target up (server, local desktop, oauth, remote) end-to-end
beeper auth            # status / logout / email
beeper status          # readiness + endpoint reachability for selected target
beeper doctor          # diagnostics (target reachability, app state, e2ee status, update available)
beeper accounts        # list / show / add / remove / use connected chat-network accounts
beeper bridges         # list available bridges and their connection state
beeper chats           # list / search / show / start / archive / mute / pin / priority / draft / remind / focus / mark-read / rename
beeper messages        # list / search / show / context / edit / delete / export
beeper send            # send text, files, reactions
beeper contacts        # list / search merged contacts per account
beeper presence        # send typing / paused indicator
beeper media           # download attachments
beeper export          # bulk export accounts/chats/messages/transcripts/attachments
beeper watch           # stream the Desktop API WebSocket as NDJSON
beeper rpc             # newline-delimited JSON command RPC over stdin/stdout — the script-friendly transport
beeper api             # raw HTTP — `api get / post / request <path>` against the selected target
beeper config          # get / set / reset / path local CLI config
beeper plugins         # CLI plugins
beeper install         # download + install Beeper Desktop / Server runtimes
beeper update          # check / install Beeper updates
beeper completion      # shell completion script
beeper docs            # open online docs
beeper man             # print command manual
```

`beeper <topic> --help` and `beeper man <topic>` are reliable for exact flag lists. The CLI is built on oclif and self-documents.

### High-value command cheatsheet

```bash
# Discovery
beeper status                                   # is the target ready?
beeper accounts list --json                     # connected networks + accountIDs
beeper bridges --json                           # bridges available

# Reading
beeper chats list --account whatsapp --limit 20 --json
beeper chats show --chat '!FhbG0...:beeper.local' --max-participants 50 --json
beeper messages list --chat <selector> --limit 50 --json
beeper messages search "invoice" --account whatsapp --limit 50 --json
beeper messages search --chat-type group --sender others "meeting"
beeper messages context --chat <selector> --id <messageID> --before 5 --after 5 --json
beeper messages export --chat <selector> --output thread.json   # whole thread, attachments included
beeper contacts --account whatsapp --query "Avi" --limit 10 --json

# Writing
beeper send "Hi there" --chat <selector>
beeper send --chat <selector> --file ./photo.jpg
beeper send --chat <selector> --reaction 👍 --reply-to <messageID>
beeper messages edit --chat <selector> --id <messageID> --text "edited body"
beeper messages delete --chat <selector> --id <messageID>

# Realtime
beeper watch --json                             # NDJSON stream of chat/message upserts/deletes
beeper rpc                                      # bidirectional JSON-RPC for long-running agents

# Raw API escape hatches (when no subcommand exists)
beeper api get  /v1/info
beeper api get  "/v1/search?query=test&limit=3"
beeper api post /v1/chats/<encodedChatID>/messages -d '{"text":"hi"}'
beeper api request -X PUT /v1/chats/<id>/messages/<mid> -d '{"text":"edited"}'
```

`<selector>` for `--chat` accepts: full chat ID, `localChatID` (e.g. `4969`), exact title, or any title substring. With ambiguity, pass `--pick <N>` (1-indexed) — never re-grep manually.

---

## Runbook: point the CLI at a *running* Beeper Desktop

This is the path you want when:

- Beeper Desktop is already open and signed in on the workstation.
- You don't want to spin up a separate managed Beeper Server (`23374`) — or that server is stuck `initializing`.
- You want every CLI command to run against the live Desktop session at `127.0.0.1:23373`.

Field-tested 4-step procedure (Linux). macOS / Windows steps 2/3 differ — see the [data-dir map](#desktop-data-dir-by-platform) below.

### 1. Verify Desktop is reachable

```bash
curl -s http://127.0.0.1:23373/v1/info | jq .app.version
# Expect e.g. "4.2.923"
```

If unreachable: open Beeper Desktop, **Settings → Developers → Beeper Desktop API**, ensure the server is enabled.

### 2. Register a CLI target

```bash
beeper targets add desktop desktop --port 23373
```

This writes `~/.beeper/targets/desktop.json`. **It will fill in a synthetic `dataDir` under `~/.beeper/profiles/desktop/desktop/` that does NOT contain your real Desktop session.**

### 3. Fix the `dataDir` so the CLI can find your real session

Edit `~/.beeper/targets/desktop.json` and replace BOTH `dataDir` fields with the platform-correct location (see table below).

```jsonc
{
  "id": "desktop",
  "type": "desktop",
  "name": "desktop",
  "baseURL": "http://127.0.0.1:23373",
  "managed": true,
  "dataDir": "/home/<you>/.config/BeeperTexts",          // ← FIX
  "profile": "desktop",
  "runtime": {
    "install": "desktop",
    "dataDir": "/home/<you>/.config/BeeperTexts",        // ← FIX
    "port": 23373
  },
  "serverEnv": "production",
  "port": 23373
}
```

Alternative (avoids editing JSON): delete both `dataDir` fields entirely so the CLI falls back to its built-in auto-detect (which IS correct — see [data-dir map](#desktop-data-dir-by-platform)).

You can also point auto-detect at a non-default location with `BEEPER_USER_DATA_DIR=...`, but only when `target.dataDir` is unset.

### 4. Mint and inject an API token (the only currently-reliable auth path)

In Beeper Desktop UI: **Settings → Developers → Approved connections → +**. Copy the resulting `bdapi_...` token.

Inject it. **Pick one** of:

```bash
# (a) Per-shell, transient — best for ad-hoc scripts:
export BEEPER_ACCESS_TOKEN="bdapi_..."
beeper status --target desktop --base-url http://127.0.0.1:23373

# (b) Persisted on the target — best for multi-agent setups:
#     edit ~/.beeper/targets/desktop.json and add:
#       "auth": { "accessToken": "bdapi_...", "source": "user-provided", "tokenType": "Bearer" }
beeper auth status --target desktop          # should now say "✓ signed in"
```

### 5. Smoke-test

```bash
beeper accounts --target desktop --json | jq '.data[].network'
beeper chats list --target desktop --account whatsapp --limit 5 --json | jq '.data[].title'
```

If both return data, every other read/write command will work too.

### Optional: make `desktop` the default target

```bash
beeper targets use desktop
```

After this, `--target desktop` is no longer needed on every call.

### Cleanup / reverting

```bash
beeper targets use beeper-server          # restore previous default
beeper targets remove desktop              # forget the target completely
```

### Desktop data-dir by platform

The Desktop's signed-in session lives in `index.db` under:

| Platform | Path |
|---|---|
| Linux | `${XDG_CONFIG_HOME:-~/.config}/BeeperTexts` |
| macOS | `~/Library/Application Support/BeeperTexts` (and any `BeeperTexts-*` siblings) |
| Windows | `%APPDATA%/BeeperTexts` |
| Override | `BEEPER_USER_DATA_DIR=<path>` (consulted only when `target.dataDir` is unset) |

Inside that dir, `index.db` is a SQLite database with a `key_values` table. Useful keys:

- `beeperState` — Matrix login state (user_id, device_id, **`access_token` is the Matrix `syt_*` token, NOT a Beeper API token**, secret-storage flags, `first_sync_done`, etc.).
- `conn:clients` — registered OAuth clients (one row per Approved Connection).
- `bridgeAccounts` — connected chat-network accounts metadata.

---

## Server target vs Desktop target — when to use which

| | `beeper-server` (managed Server, port 23374) | `desktop` (running Desktop, port 23373) |
|---|---|---|
| Lifecycle | CLI starts/stops a headless beeper-server process for you | You launch Beeper Desktop yourself; CLI just talks to it |
| Auth bootstrap | `beeper setup --server` walks you through Matrix login + e2ee verification | Manual `bdapi_*` token from the UI (currently the only reliable path) |
| First-sync time | Can sit in `state: "initializing"` for a long time on a fresh install — many endpoints (`getChat`, `listMessages`, `chats list`, `contacts list`) return `500` / `[]` until first sync + e2ee finish | Already synced if you've been using the app — works immediately |
| Headless / CI | ✅ runs without a desktop session | ❌ requires the Electron app running |
| Verdict | Use when there's no GUI session, or you want a long-lived background agent | **Default choice on a workstation where Beeper Desktop is already open and signed in.** Faster, more reliable, more endpoints work today. |

Quick diagnosis when commands return weird errors:

```bash
beeper status --target <name>      # human summary
beeper doctor                       # full readiness JSON: app state, matrix, e2ee, secrets, action hints
```

If `doctor` shows `app.state: "initializing"` and you're on a server target, you're hitting a sync-not-finished problem, not an auth problem. Switch to a desktop target if Beeper Desktop is available.

---

## Known broken / quirky paths (CLI 0.6.x, Desktop 4.2.x)

| Path | Status | Workaround |
|---|---|---|
| `beeper setup --target desktop --local` | Reads Matrix `syt_*` from `beeperState.access_token`; Desktop `/v1/*` rejects it as `Invalid token`. `beeper auth status` will lie and say "✓ signed in". | Use the manual `bdapi_*` token flow above. |
| `beeper setup --target desktop --oauth` | Returns `OAuth authorization failed: server_error` instantly — Desktop side blows up before any browser interaction in some environments. | Use the manual `bdapi_*` token flow above. |
| `beeper targets add desktop` synthesizes a wrong `dataDir` | Affects all platforms when there's no managed-runtime install at the synthetic path. | Edit the target JSON or delete `dataDir`. |
| `/v1/app/setup` returns 401 with a `bdapi_*` token | Internal endpoint requires a different scope; only affects `beeper status` / readiness display. | Cosmetic — every other endpoint works. Ignore the "target unreachable" banner if `accounts list` succeeds. |
| `/v1/chats` empty / `getChat` returns 500 on a managed `server` target stuck `initializing` | Server hasn't finished first sync. | Wait for sync, or switch to the `desktop` target. |
| Sender ID mismatch in WhatsApp groups | Messages identify senders by WhatsApp **LIDs** (`@whatsapp_lid-...`), but `chats show` participant lists return phone numbers. | Cross-reference participant `id` ↔ message `senderID` requires a separate lookup; not yet exposed as a single CLI call. |

---

## Useful one-liners

Latest 20 messages on a network with chat names:

```bash
beeper messages search --account whatsapp --limit 20 --json --full | \
  jq -r '.data[] | "\(.timestamp)\t\(.chatID)\t\(.senderName)\t\(.text)"'

# Resolve chatID → title in one pass:
beeper messages search --account whatsapp --limit 20 --json | \
  jq -r '[.data[].chatID] | unique | .[]' | \
  xargs -I{} beeper chats show --chat {} --json --quiet | \
  jq -r '.data | "\(.id)\t\(.title)"'
```

Stream new messages and react with a script (long-running):

```bash
beeper watch --json --target desktop | \
  while IFS= read -r line; do
    echo "$line" | jq -c 'select(.type=="message.upserted") | .data'
  done
```

Send and edit:

```bash
beeper send "first version" --chat 'Project Foo' --target desktop --json | jq -r '.data.id' > /tmp/mid
beeper messages edit --chat 'Project Foo' --id "$(cat /tmp/mid)" --text "second version"
```

Bulk export a thread for offline analysis:

```bash
beeper messages export --chat <selector> --output thread.json
```

---

## When to drop down from CLI to SDK / curl

The CLI is the right tool for **almost every shell-level interaction**. Drop down when you need:

- Tight loops with thousands of calls per minute → use the TS / Python / Go SDK in-process to avoid spawning a binary per call.
- Custom WebSocket subscription logic with backpressure → connect to `ws://127.0.0.1:23373/v1/ws` directly (see `references/websocket.md`).
- A deployed agent that needs to run on a machine without `npm` or Node.js → ship a compiled SDK binary instead.

For everything else — discovery, scripting, ad-hoc recipes, agent prompts that shell out — start with `beeper`.
