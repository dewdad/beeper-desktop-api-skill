# Bridges & self-hosting (bbctl)

Beeper Desktop connects to chat networks via Matrix bridges that Beeper hosts for you by default. Users who want to run bridges on their own infrastructure use `bbctl` — the Beeper Bridge Manager — which runs bridges under the user's own account so the Desktop API (and everything in this skill) still works against them transparently.

This page is reference only. The self-hosted bridge surface is NOT part of the Desktop API — it's a separate tool that the Desktop API consumes behind the scenes.

## `bbctl` overview

**Supported OS:** Linux and macOS on amd64 or arm64. Windows is supported via WSL.

Install and auth:

```bash
# Install per https://github.com/beeper/bridge-manager (Homebrew / prebuilt binaries)
bbctl login
```

Run or remove a bridge:

```bash
bbctl run sh-<bridgename>       # spin up a self-hosted bridge
bbctl delete sh-<bridgename>    # tear it down
```

Data is stored at `~/.local/share/bbctl` by default.

## Official bridges

| Network | Bridge identifier(s) |
|---|---|
| Telegram | `telegram` |
| WhatsApp | `whatsapp` |
| Signal | `signal` |
| Discord | `discord` |
| Slack | `slack` |
| Google Messages | `gmessages`, `rcs`, `sms` |
| Google Voice | `gvoice` |
| Meta (Instagram / Facebook) | `meta`, `instagram`, `facebook` |
| Google Chat | `googlechat` |
| X / Twitter | `twitter` |
| Bluesky | `bluesky`, `bsky` |
| iMessage | `imessage`, `imessagego` |
| LinkedIn | `linkedin` |
| IRC | `heisenbridge`, `irc` |

## How this relates to the Desktop API

Whether a network is bridged by Beeper's hosted infrastructure or by a user's self-hosted `bbctl run sh-<bridge>` instance, the bridge still shows up as a regular **account** in `GET /v1/accounts`. All the same `chatID` / `messageID` / `accountID` semantics apply — you do not need different code paths for hosted vs self-hosted bridges.

## Protocol coverage (from the Android content-provider docs, which mirror the same bridge set)

The following protocol identifiers are full-featured: `whatsapp`, `telegram`, `signal`, `beeper`, `matrix`, `discord`, `slack`, `gmessages`. Other networks are supported but may have reduced feature coverage on a per-network basis.

## When to use this page

- You're debugging a user whose account is self-hosted and want to understand the bridge lifecycle.
- You need the exact bridge identifier to pass to `bbctl run` or to match against `account.accountID` prefixes (e.g. `local-whatsapp_*`, `local-telegram_*`).
- You're documenting a feature that must work identically across hosted and self-hosted setups.
