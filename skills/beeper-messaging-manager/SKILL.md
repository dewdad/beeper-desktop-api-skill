---
name: beeper-messaging-manager
description: |
  Turn a Beeper Desktop install into an agent-managed messaging hub. Ships a
  one-command installer plus two proven standing automations: (1) a REALTIME
  ALERT watcher — a supervised WebSocket daemon that fires instant alerts on
  1:1 DMs, VIP senders, or keywords across every network connected to Beeper
  (WhatsApp, iMessage, Telegram, Signal, Instagram, X, LinkedIn, Google
  Messages, …); and (2) a SCHEDULED DIGEST — a 3x/day ranked "what did I miss"
  brief. Portable across Hermes Agent and OpenCode, and across Linux / macOS /
  Windows. Load when the user wants their agent to monitor, alert on, digest,
  or otherwise manage their consolidated Beeper messaging on a recurring /
  always-on basis. For the raw Beeper Desktop API surface (endpoints, CLI
  flags, SDKs, WebSocket event shapes) load the sibling `beeper-desktop-api`
  skill FIRST — this skill is the orchestration + supervision + install layer
  on top of it.
license: MIT
compatibility: |
  Requires Beeper Desktop >= 4.1.169 with Settings -> Developers -> Beeper
  Desktop API enabled, plus the `beeper` CLI (@beeper/cli), `jq`, and Python
  3.11+. Supervision auto-wires on Linux (systemd --user) and macOS (launchd);
  Windows prints Task Scheduler steps. Digest scheduling auto-detects Hermes
  (cron tool) and OpenCode, and degrades to plain crontab instructions on a
  generic host.
metadata:
  version: "1.1.0"
  upstream: https://github.com/dewdad/beeper-desktop-api-skill
---

# Beeper Messaging Manager

The **orchestration + supervision + install** layer on top of the Beeper
Desktop API. It packages two field-tested standing automations and a single
installer that wires them into whatever agent/OS you're on.

> **Load `beeper-desktop-api` FIRST** for the API itself — targets, tokens,
> CLI flags, WebSocket event shapes, endpoint schemas, and every gotcha. This
> skill deliberately does NOT re-document those; it builds on them.

## What you get

1. **Realtime alert watcher** (`templates/watcher.py`) — a long-lived process
   that connects to the Beeper WebSocket, subscribes to all chats, and fires an
   instant alert when an *incoming* message is a 1:1 DM, from a VIP sender, or
   contains a VIP keyword. Delivered via Telegram or any command (`ALERT_CMD`).
2. **Scheduled digest** (`templates/digest.sh` + `templates/digest_prompt.md`)
   — a collector that ranks unread across all networks, plus a prompt that a
   scheduled agent run reasons into a phone-glance brief (DMs first, noisy
   groups rolled to one line, original languages preserved).
3. **One-command installer** (`scripts/install.py`) — detects OS + host agent,
   verifies prerequisites, materializes an isolated automation dir + venv,
   supervises the watcher, registers the digest schedule, and self-tests. It
   automates what it can and prints exact MANUAL steps for what it can't
   (minting a token in the GUI, a missing supervisor, etc.) — it never fakes
   success.

## Install (the fast path)

```bash
python3 skills/beeper-messaging-manager/scripts/install.py
```

> **Requirements:** Python **3.11+** with `venv` + `pip` (Debian/Ubuntu:
> `sudo apt install python3.12 python3.12-venv`), the `beeper` CLI, and `jq`.
> Invoke with `python3` (or a versioned `python3.12`) — bare `python` may point
> at an unsupported interpreter. The installer version-gates itself and prints
> exact per-OS install commands if Python is too old or missing — it never
> crashes with a bare traceback. If `venv` can't be created it falls back to
> your system interpreter when it already has `websockets`, else prints the one
> command to finish.

Re-runnable and idempotent. Useful flags:

| Flag | Effect |
|---|---|
| `--dry-run` | Show every action without changing anything (safe first pass). |
| `--dir DIR` | Automation base dir (default `~/.beeper-automation`). |
| `--tg-token T --tg-chat C` | Write Telegram delivery creds into `alert.env`. |
| `--no-supervise` | Copy files + schedule, but don't touch systemd/launchd. |
| `--no-schedule` | Set up the watcher only; skip the digest schedule. |
| `--force-config` | Overwrite an existing `vip.json` / `alert.env`. |

Run `--dry-run` first to see exactly what it will do and which steps need a
human, then run it for real.

## The decision: which surface for which need

- **"Alert me the moment X arrives" -> the realtime watcher.** A persistent
  WebSocket daemon, supervised. Not cron (interval lag), not MCP.
- **"N times a day, what did I miss" -> the scheduled digest.** A scheduled
  agent run shells the `beeper` CLI and reasons over ranked unread. No MCP
  needed — a headless scheduled run already has a terminal.
- **Interactive Beeper tools resident during a live chat with the agent** ->
  the only case where registering the Beeper MCP server earns its place
  (see `beeper-desktop-api` -> `references/mcp-server.md`).

Rule of thumb: **WS daemon for realtime, cron+CLI for polling, MCP almost
never** for standing automation.

## Portability model (how it targets your setup)

The installer resolves two axes and wires accordingly; both degrade to printed
instructions rather than failing:

| | Detection | Watcher supervision | Digest scheduling |
|---|---|---|---|
| **Linux** | `systemctl`, `~/.config/systemd/user` | systemd --user unit, `enable-linger` | (per host agent) |
| **macOS** | `launchctl`, `~/Library/LaunchAgents` | launchd plist | (per host agent) |
| **Windows** | — | MANUAL: Task Scheduler steps printed | MANUAL: Task Scheduler / WSL |
| **Hermes** | `hermes` on PATH / `~/.hermes` | (per OS) | MANUAL: register via the `cronjob` tool, `deliver=telegram`, prompt from `digest_prompt.md` |
| **OpenCode** | `opencode` on PATH / `~/.config/opencode` | (per OS) | MANUAL: crontab line invoking `opencode run --prompt-file` |
| **Generic** | fallback | (per OS) | MANUAL: plain crontab running the collector |

Digest scheduling is intentionally left as a guided MANUAL step on every host:
each agent's job registration + delivery routing differs enough that a printed,
copy-pasteable instruction is more honest than a fragile auto-wire. The
installer prints the exact schedule, prompt path, and delivery flag for the
detected host.

## The user-facing tuning knob: `vip.json`

The whole alert brain is data-driven and re-read on **every** event (no
restart). Edit `<automation-dir>/vip.json`:

- `alert_all_dms` — `true` = every 1:1 DM on any network alerts.
- `vip_senders[]` — case-insensitive substring vs `senderName`/`senderID`;
  alerts even in groups.
- `vip_keywords[]` — case-insensitive substring vs message text; alerts in any
  chat. UTF-8 (Hebrew, Arabic, emoji) works.
- `mute_networks[]` — network/accountID substrings to skip for alerts (digest
  still covers them).
- `mute_chats[]` — chatIDs or exact titles to never alert on.

## CRITICAL pitfalls (learned building this — don't relearn them)

- **Always `--target desktop` on EVERY `beeper` CLI call.** The default target
  on most workstations is the managed `beeper-server` (:23374), which is often
  unreachable or still `initializing`; commands then silently return `[]`,
  looking like an empty inbox. The bundled `digest.sh` already forces
  `--target desktop`. An empty result on a `connected` account is a target
  problem first, an empty inbox second. (Full detail: `beeper-desktop-api`.)
- **WS delivers ZERO events until you subscribe.** After the `ready` frame the
  client MUST send `{"type":"subscriptions.set","requestID":"..","chatIDs":["*"]}`.
  A watcher that connects and waits sees the handshake and silence forever.
- **Suppress your own sends.** Every `message.upserted` entry carries
  `isSender`; skip `isSender==true` or the watcher alerts on the agent's own
  outbound (and you can't self-test by messaging yourself — it's filtered).
- **`beeper watch` (CLI) ignores `--target` (upstream bug, CLI 0.6.x).** This
  skill uses the raw WS daemon in `watcher.py` precisely to sidestep that. If
  you ever must use the CLI watch, pass `--base-url http://127.0.0.1:23373` +
  the desktop token via `BEEPER_ACCESS_TOKEN`, never `--target`.
- **Scheduler/supervisor PATH is narrower than interactive.** `beeper` and
  `jq` may not be on it. `digest.sh` honors `BEEPER_BIN`; units use absolute
  paths. If the smoke-test can't find `beeper`, set `BEEPER_BIN` to its
  absolute path (often `~/.npm-global/bin/beeper`).
- **systemd --user needs linger to survive logout/reboot.** The installer runs
  `loginctl enable-linger`; if it couldn't (no privileges), the watcher stops
  at logout. Check `loginctl show-user "$USER" | grep Linger`.
- **Token kinds differ.** The desktop target token starts `bdapi_…` and lives
  at `~/.beeper/targets/desktop.json -> .auth.accessToken`. The Matrix `syt_…`
  token is NOT accepted by `/v1/*`. Don't confuse them.
- **Hermes cron cannot deliver to a WebUI session.** A job left at
  `deliver=origin` from a WebUI chat fails silently (`unknown platform 'webui'`)
  — the run succeeds but output goes nowhere. Use `deliver=telegram` (digests
  are markdown, render natively) or `deliver=local`.
- **Message `text` may be HTML.** WhatsApp broadcast + Matrix bridges deliver
  `<strong>`, `<br>`, entities. The watcher/digest strip it; any custom
  consumer must too.

## Verify before declaring done

The installer does this automatically; to check by hand:

- **Alert logic:** `<dir>/.venv/bin/python scripts/test_matches.py
  <dir>/watcher.py` -> expect `ALL PASS` (DM / VIP / keyword / mute / self).
- **Collector:** `BEEPER_BIN=<beeper> bash <dir>/digest.sh 3 1` -> real ranked
  JSON, not `{"chats":[]}` (empty => target/token issue, see pitfalls).
- **Watcher (Linux):** `systemctl --user status beeper-watcher` shows
  `active (running)` and `<dir>/watcher.log` shows
  `[connected] subscribed to all chats`.
- **Watcher (macOS):** `launchctl list | grep com.beeper.watcher`.
- **End-to-end alert:** have someone send you a DM (you can't self-test — your
  own sends are filtered by `isSender`); watch for the Telegram alert / log line.

## Support files

- `scripts/install.py` — the one-command, host-aware installer. Version-gates
  to Python 3.11+ with a friendly per-OS message before doing anything.
- `scripts/test_matches.py` — re-runnable unit test of the alert match logic.
- `templates/watcher.py` — the realtime WS alert daemon (portable).
- `templates/digest.sh` — the ranked-unread collector.
- `templates/digest_prompt.md` — the reasoning prompt for the scheduled run.
- `templates/vip.json` — the editable alert-tuning config (the user knob).
- `templates/alert.env` — delivery credentials (Telegram or `ALERT_CMD`).
- `templates/beeper-watcher.service` — systemd --user unit (Linux).
- `templates/com.beeper.watcher.plist` — launchd agent (macOS).
