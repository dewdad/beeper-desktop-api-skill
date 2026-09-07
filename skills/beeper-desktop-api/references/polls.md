# Experimental polls through Beeper-backed chats

## Contents

1. [Status and scope](#status-and-scope)
2. [Why the normal Desktop API cannot send polls](#why-the-normal-desktop-api-cannot-send-polls)
3. [Safety model](#safety-model)
4. [Check the target chat](#check-the-target-chat)
5. [Send with the bundled helper](#send-with-the-bundled-helper)
6. [Finalized Matrix event shape](#finalized-matrix-event-shape)
7. [Verify the result](#verify-the-result)
8. [Unsupported operations and caveats](#unsupported-operations-and-caveats)
9. [Troubleshooting](#troubleshooting)

## Status and scope

**Experimental, bridge-specific workaround.** Use this only when the target chat advertises native poll support and the documented Beeper Desktop `/v1` writer still lacks a poll operation.

Verified behavior:

- WhatsApp chats can report `capabilities.poll == 2`.
- A finalized Matrix `m.poll.start` event sent into such a Beeper room is accepted.
- Beeper reads it back as `m.poll.start` and indexes the stable `m.poll` content as message type `POLL`, preserving the question, answers, selection limit, and fallback text.

This proves Beeper processed the event as a poll. Before relying on it operationally, test recipient-side rendering in a low-stakes chat using the native WhatsApp client. A self-chat alone does not prove every bridge/account/client combination.

## Why the normal Desktop API cannot send polls

The current `POST /v1/chats/{chatID}/messages` request schema accepts `text`, `replyToMessageID`, and one `attachment`; the official CLI similarly exposes text, file, voice, sticker, and reaction sends. Neither exposes a poll writer even when chat metadata says polls are supported.

The workaround sends a finalized Matrix poll event directly to the Matrix homeserver associated with the Beeper session:

```text
PUT /_matrix/client/v3/rooms/{roomId}/send/m.poll.start/{txnId}
```

Do not call this endpoint with `POST`. Use a unique transaction ID for retry safety.

## Safety model

Two different credentials are involved:

| Credential | Typical prefix | Used for |
|---|---|---|
| Beeper Desktop API token | `bdapi_…` | Read the exact chat and verify `capabilities.poll == 2` before sending |
| Matrix access token | commonly `syt_…` | Send and read back the `m.poll.start` event at the Matrix homeserver |

Never print either token. Never substitute one for the other.

Prefer supplying the Matrix credential explicitly through `BEEPER_MATRIX_ACCESS_TOKEN`. The helper can read Beeper Desktop's local Matrix session from `index.db`, but only when `--allow-local-session` is passed. That is an opt-in implementation-detail fallback: it depends on Beeper's private local storage layout and can break after an app update.

The helper is **dry-run by default**. It performs no write unless `--send` is supplied.

## Check the target chat

Resolve a chat selector to an exact room ID, inspect it, and confirm all of:

- The `id` is the intended room—do not send using an ambiguous title.
- `isReadOnly` is false.
- `capabilities.poll` equals `2` (native/support level), not merely present or truthy.

```bash
beeper chats show --target desktop --chat '<exact selector>' --json --full
```

For a WhatsApp self-chat, resolve the account's own number rather than guessing from titles:

```bash
beeper accounts list --target desktop --json --full
beeper contacts search '<own E.164 number>' --target desktop --account whatsapp --json --full
beeper chats start '<resolved participant ID>' --target desktop --account whatsapp --json --full --yes
```

`chats start` returns an existing DM when one already exists. Read its returned `id`, participants, account, and capabilities before proceeding.

## Send with the bundled helper

The script uses only Python's standard library.

### 1. Dry-run first

```bash
python3 scripts/send_poll.py \
  '!exactRoomID:beeper.local' \
  'Where should we meet?' \
  'Office' 'Cafe' 'Online'
```

This prints the exact event content and exits without reading tokens or making network requests.

### 2. Preferred credential path

```bash
export BEEPER_ACCESS_TOKEN='bdapi_…'
export BEEPER_MATRIX_ACCESS_TOKEN='syt_…'

python3 scripts/send_poll.py \
  '!exactRoomID:beeper.local' \
  'Where should we meet?' \
  'Office' 'Cafe' 'Online' \
  --homeserver 'https://matrix.beeper.com' \
  --send
```

The Desktop token can also come from the configured `desktop` CLI target. The Matrix token must be supplied with its homeserver.

### 3. Explicit local-session fallback

On a workstation with Beeper Desktop's default Linux data directory:

```bash
python3 scripts/send_poll.py \
  '!exactRoomID:beeper.local' \
  'Where should we meet?' \
  'Office' 'Cafe' 'Online' \
  --allow-local-session \
  --send
```

For a non-default location, add `--data-dir /path/to/BeeperTexts`. The helper
always uses the homeserver stored with that local session; it rejects a
simultaneous `--homeserver` override to prevent sending the local token to a
different host.

### Options

- `--max-selections N` — defaults to one; must not exceed the answer count.
- `--undisclosed` — hide running vote totals using `m.undisclosed`.
- `--timeout SECONDS` — HTTP timeout, default 30.
- The Desktop capability check is intentionally fixed to loopback at
  `http://127.0.0.1:23373`, preventing a Desktop token from being sent to an
  arbitrary host.

Successful output is token-free JSON:

```json
{
  "event_id": "$event:beeper.local",
  "room_id": "!room:beeper.local",
  "transaction_id": "beeper-poll-…",
  "verified": true
}
```

## Finalized Matrix event shape

Use the finalized `m.poll.start` format—not early MSC drafts that put plain strings in `question` or use `{id, label}` answers:

```json
{
  "m.text": [
    {
      "mimetype": "text/plain",
      "body": "Where should we meet?\n1. Office\n2. Cafe"
    }
  ],
  "m.poll": {
    "max_selections": 1,
    "question": {
      "m.text": [{"body": "Where should we meet?"}]
    },
    "kind": "m.disclosed",
    "answers": [
      {
        "m.id": "unique-answer-id-1",
        "m.text": [{"body": "Office"}]
      },
      {
        "m.id": "unique-answer-id-2",
        "m.text": [{"body": "Cafe"}]
      }
    ]
  }
}
```

Every `m.id` must be unique. The top-level `m.text` block is the plain-text
fallback. Do not use the older unstable `org.matrix.msc3381.*` names, and do
not use the hybrid `{ "m.poll.start": ..., "org.matrix.msc1767.text": ... }`
shape sometimes shown in generated examples. Matrix limits a poll to 20 answer
options; the helper rejects larger inputs rather than relying on receiver-side
truncation.

## Verify the result

The helper does not treat HTTP 200 as completion. It reads back the exact event ID and verifies:

- matching event ID and room ID;
- event type `m.poll.start`;
- poll content equal to the submitted poll content.

For additional local inspection:

```bash
beeper messages list --target desktop --chat '<room ID>' --limit 5 --json --full
```

The Desktop projection may omit poll-specific fields from CLI output. A local Beeper database can classify the row as `POLL`, but querying private tables is diagnostic only and must not become an application dependency.

For true end-to-end validation, open the destination in native WhatsApp and confirm that it renders as an interactive poll.

## Unsupported operations and caveats

- The bundled helper creates polls only. Voting and closing are intentionally not exposed until separately tested end to end.
- Do not claim delivery from Matrix acceptance alone. The read-back proves event persistence; native-client inspection proves bridge rendering.
- Poll support is chat/network-specific. Reject targets without `capabilities.poll == 2`.
- The local Matrix token fallback is sensitive and unstable. Keep file permissions restrictive and never copy `index.db` into a project or diagnostic archive.
- This bypasses the documented `/v1` message writer. Re-test after Beeper Desktop or bridge upgrades, and prefer a future official `/v1`/CLI poll operation when one appears.

## Troubleshooting

### `native polls are not supported in the target chat`

The exact chat did not advertise `capabilities.poll == 2`. Do not force-send; choose a supported destination.

### `the target chat is read-only`

Broadcast/news channels may report poll capability generically while forbidding writes. Use a writable chat.

### `--homeserver is required with an explicit Matrix token`

Supply the homeserver paired with that Matrix session, usually `https://matrix.beeper.com` for Beeper-hosted accounts.

### `Beeper index database not found`

Pass the actual Beeper Desktop data directory or use an explicit Matrix token. The helper never searches the filesystem broadly for credential databases.

### HTTP 401

Check token type. `bdapi_…` authenticates Desktop `/v1`; the Matrix client endpoint requires the Matrix access token.

### HTTP 200 but no native poll

Matrix persistence is not equivalent to bridge delivery. Confirm the exact room belongs to the intended WhatsApp account, verify `capabilities.poll == 2`, then inspect the destination in native WhatsApp. Treat failure as an incompatible bridge/client version and stop using the workaround there.
