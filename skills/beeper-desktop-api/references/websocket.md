# WebSocket API (experimental)

Realtime event stream for chats and messages. Experimental — the schema may evolve. The URL is advertised by `GET /v1/info` as `endpoints.ws_events`.

## Contents

- [Connection](#connection)
- [Client → server commands](#client---server-commands)
- [Server → client control messages](#server---client-control-messages)
- [Domain events](#domain-events)
- [Node.js client example](#nodejs-client-example)
- [Python client example](#python-client-example)

## Connection

```
URL:    ws://localhost:23373/v1/ws
Header: Authorization: Bearer <your_token>
```

The server sends a `ready` control message as soon as the handshake is complete. No events are delivered until the client sends a `subscriptions.set` command.

## Client -> server commands

### `subscriptions.set`

Replaces the current subscription set. Send this once after `ready`, and again any time you want to change what you receive.

```json
{
  "type": "subscriptions.set",
  "requestID": "req-1",
  "chatIDs": ["*"]
}
```

| Field | Type | Description |
|---|---|---|
| `type` | string | Always `"subscriptions.set"`. |
| `requestID` | string | Echoed back in the server's `subscriptions.updated` / `error` response. |
| `chatIDs` | string[] | Chat IDs to subscribe to. `["*"]` = all chats. `[]` = pause (receive no domain events). |

**Rules.**
- `"*"` cannot be combined with specific chat IDs. Either send `["*"]` alone or a concrete list.
- Each new `subscriptions.set` call fully replaces the previous subscription set.

## Server -> client control messages

### `ready`

Sent once immediately after the connection is authenticated.

```json
{
  "type": "ready",
  "version": 1,
  "chatIDs": []
}
```

### `subscriptions.updated`

Acknowledges a successful `subscriptions.set`.

```json
{
  "type": "subscriptions.updated",
  "requestID": "req-1",
  "chatIDs": ["*"]
}
```

### `error`

Sent when a command fails (bad shape, invalid chat ID combo, etc.).

```json
{
  "type": "error",
  "requestID": "req-1",
  "code": "invalid_subscription",
  "message": "'*' cannot be combined with specific chat IDs"
}
```

## Domain events

All domain events share a flat envelope:

```ts
interface DomainEvent {
  type: 'chat.upserted' | 'chat.deleted' | 'message.upserted' | 'message.deleted';
  seq: number;          // monotonic per-connection sequence
  ts: number;           // unix ms
  chatID: string;
  ids: string[];        // affected entity IDs (chat IDs or message IDs)
  entries?: object[];   // hydrated full payloads (upsert only)
}
```

### `chat.upserted`

```json
{
  "type": "chat.upserted",
  "seq": 12,
  "ts": 1760000000123,
  "chatID": "!NCdzlIaMjZUmvmvyHU:beeper.com",
  "ids": ["!NCdzlIaMjZUmvmvyHU:beeper.com"],
  "entries": [
    {
      "id": "!NCdzlIaMjZUmvmvyHU:beeper.com",
      "accountID": "local-whatsapp_ba_EvYDBBsZbRQAy3UOSWqG0LuTVkc",
      "network": "WhatsApp",
      "title": "Gabe",
      "type": "single",
      "unreadCount": 0,
      "lastActivity": 1760000000000
    }
  ]
}
```

### `chat.deleted`

```json
{
  "type": "chat.deleted",
  "seq": 13,
  "ts": 1760000001000,
  "chatID": "!NCdzlIaMjZUmvmvyHU:beeper.com",
  "ids": ["!NCdzlIaMjZUmvmvyHU:beeper.com"]
}
```

No `entries` field — deletions carry IDs only.

### `message.upserted`

Hydrated with full `Message` payloads (including `attachments` when retrievable). Events without a retrievable full payload are skipped entirely rather than emitted with partial data.

```json
{
  "type": "message.upserted",
  "seq": 14,
  "ts": 1760000002000,
  "chatID": "!NCdzlIaMjZUmvmvyHU:beeper.com",
  "ids": ["$abc123"],
  "entries": [
    {
      "id": "$abc123",
      "messageID": "$abc123",
      "chatID": "!NCdzlIaMjZUmvmvyHU:beeper.com",
      "accountID": "local-whatsapp_ba_EvYDBBsZbRQAy3UOSWqG0LuTVkc",
      "senderID": "wa:+14155550123",
      "senderName": "Gabe",
      "text": "on the way",
      "timestamp": 1760000002000,
      "sortKey": "0:0001",
      "isSender": false,
      "attachments": []
    }
  ]
}
```

### `message.deleted`

```json
{
  "type": "message.deleted",
  "seq": 15,
  "ts": 1760000003000,
  "chatID": "!NCdzlIaMjZUmvmvyHU:beeper.com",
  "ids": ["$abc123"]
}
```

No `entries` — deletions carry IDs only.

## Node.js client example

```js
import WebSocket from 'ws';

const ws = new WebSocket('ws://localhost:23373/v1/ws', {
  headers: { Authorization: `Bearer ${process.env.BEEPER_ACCESS_TOKEN}` },
});

ws.on('open', () => {
  console.log('connected');
});

ws.on('message', (buf) => {
  const evt = JSON.parse(buf.toString());
  if (evt.type === 'ready') {
    ws.send(JSON.stringify({ type: 'subscriptions.set', requestID: 'r1', chatIDs: ['*'] }));
  } else if (evt.type === 'message.upserted') {
    for (const m of evt.entries ?? []) {
      console.log(`[${m.senderName}] ${m.text}`);
    }
  }
});

ws.on('error', console.error);
```

## Python client example

```python
import asyncio
import json
import os

import websockets

async def main():
    headers = {"Authorization": f"Bearer {os.environ['BEEPER_ACCESS_TOKEN']}"}
    async with websockets.connect(
        "ws://localhost:23373/v1/ws", extra_headers=headers
    ) as ws:
        ready = json.loads(await ws.recv())
        assert ready["type"] == "ready"

        await ws.send(json.dumps({
            "type": "subscriptions.set",
            "requestID": "r1",
            "chatIDs": ["*"],
        }))

        async for raw in ws:
            evt = json.loads(raw)
            if evt.get("type") == "message.upserted":
                for m in evt.get("entries", []):
                    print(f"[{m.get('senderName')}] {m.get('text')}")

asyncio.run(main())
```
