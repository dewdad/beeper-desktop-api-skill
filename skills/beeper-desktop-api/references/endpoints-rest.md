# Beeper Desktop REST API — Complete Endpoint Reference

Base URL: `http://localhost:23373`
Auth header (every request): `Authorization: Bearer $BEEPER_ACCESS_TOKEN`
Content-Type for request bodies: `application/json` (except `/v1/assets/upload` which is `multipart/form-data`).

All `/v0/*` paths are deprecated as of Beeper Desktop 4.1.294. Use `/v1/*`. Every `/v1` endpoint below is listed with its replacement for any code still on `/v0`.

Shared error envelope (all 4xx/5xx):

```json
{ "error": "string", "code": "string?", "details": { "<key>": "string" } }
```

Universal status codes: `400` bad params, `401` missing/invalid token, `403` insufficient scope, `404` not found, `422` validation error, `429` rate limited, `500` internal error.

---

## Table of contents

1. [Server & Discovery](#server--discovery)
2. [Accounts](#accounts)
3. [Chats](#chats)
4. [Messages](#messages)
5. [Reactions](#reactions)
6. [Reminders](#reminders)
7. [Contacts](#contacts)
8. [Search](#search)
9. [Assets](#assets)
10. [App control](#app-control)
11. [OAuth](#oauth)

---

## Server & Discovery

### `GET /v1/info`

Returns app, platform, server, and endpoint discovery metadata. Use this to verify the server is up, discover WebSocket/MCP/OAuth URLs, and check server `status`.

**Auth:** required.

**Example:**

```bash
curl http://localhost:23373/v1/info \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

**Response 200:**

```ts
{
  app: {
    bundle_id: string;   // e.g. "com.automattic.beeper.desktop"
    name: string;        // "Beeper Desktop"
    version: string;     // "4.2.509"
  };
  endpoints: {
    mcp: string;         // "http://localhost:23373/v0/mcp"
    oauth: {
      authorization_endpoint: string;
      introspection_endpoint: string;
      registration_endpoint: string;
      revocation_endpoint: string;
      token_endpoint: string;
      userinfo_endpoint: string;
    };
    spec: string;        // OpenAPI spec URL
    ws_events: string;   // "ws://localhost:23373/v1/ws"
  };
  platform: {
    arch: string;        // "arm64" | "x64"
    os: string;          // "darwin" | "win32" | "linux"
    release?: string;
  };
  server: {
    base_url: string;    // "http://localhost:23373"
    hostname: string;
    mcp_enabled: boolean;
    port: number;        // 23373
    remote_access: boolean;
    status: string;      // "ok"
  };
}
```

---

## Accounts

### `GET /v1/accounts`
*(Replaces deprecated `GET /v0/get-accounts`.)*

Lists connected networks. Use `accountID` from each item to route any account-scoped action. `network` is human-readable only.

**Example:**

```bash
curl http://localhost:23373/v1/accounts \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

**Response 200** — array of:

| Field | Type | Notes |
|---|---|---|
| `accountID` | string | **Use this for routing actions.** Example: `local-whatsapp_ba_EvYDBBsZbRQAy3UOSWqG0LuTVkc` |
| `network` | string | Display name: `"WhatsApp"`, `"Telegram"`, `"Twitter/X"`, `"iMessage"`, `"Signal"`, `"Discord"`, ... |
| `user.id` | string | Stable Beeper user ID of the account owner |
| `user.username` | string? | Handle; not globally unique |
| `user.phoneNumber` | string? | E.164 when available |
| `user.fullName` | string? | Display name |
| `user.imgURL` | string? | May be temporary; download promptly if durable access needed |
| `user.email` | string? | |
| `user.cannotMessage` | boolean? | True if Beeper can't initiate messages to this identity |
| `user.isSelf` | boolean | True — this is the authenticated user's own identity |

**Example response:**

```json
[
  {
    "accountID": "local-whatsapp_ba_EvYDBBsZbRQAy3UOSWqG0LuTVkc",
    "network": "WhatsApp",
    "user": {
      "id": "ba_EvYDBBsZbRQAy3UOSWqG0LuTVkc",
      "phoneNumber": "+15551234567",
      "fullName": "Batuhan",
      "imgURL": "file:///.../attachments/113988c2...",
      "isSelf": true
    }
  },
  {
    "accountID": "local-telegram_ba_QFrb5lrLPhO3OT5MFBeTWv0x4BI",
    "network": "Telegram",
    "user": { "id": "...", "username": "batuhan", "phoneNumber": "+15559876543", "fullName": "Batuhan", "isSelf": true }
  }
]
```

---

## Chats

### `GET /v1/chats`

List chats across all accounts, sorted by last activity (most recent first). Cursor-paginated.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `accountIDs` | string[] | — | Restrict to specific accounts |
| `cursor` | string | — | Opaque cursor from a previous response |
| `direction` | `before` \| `after` | `before` | Direction relative to cursor; `before` fetches older |
| `limit` | integer | — | Page size |

**Response 200:** page of chat objects (see `schemas.md` → `Chat`). Each chat includes a `preview` field carrying the latest message (same shape as a message object).

**Example:**

```bash
curl "http://localhost:23373/v1/chats?limit=20" \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

### `POST /v1/chats`
*(Replaces `POST /v0/create-chat`.)*

Create a new chat OR start a DM from merged user data. Two modes:

- `mode: "create"` — explicit create: provide `accountID`, `type`, `participantIDs`.
- `mode: "start"` — start DM from a resolved `user` (the preferred way to DM someone from a contact record). Returns an existing chat if one exists.

**Request body:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `accountID` | string | yes | Which account hosts the new chat |
| `mode` | `"create"` \| `"start"` | no | Default is implementation-defined; set explicitly |
| `type` | `"single"` \| `"group"` | for `create` | `single` requires exactly one participant |
| `participantIDs` | string[] | for `create` | Minimum 1 |
| `title` | string | no | Group title; ignored for single on most platforms |
| `messageText` | string | no | Initial text (some platforms require this to create a chat) |
| `allowInvite` | boolean | no | For networks that support invite links |
| `user` | object | for `start` | `{ id?, email?, fullName?, phoneNumber?, username? }` |

**Response 200:**

```json
{ "chatID": "!NCdzlIaMjZUmvmvyHU:beeper.com", "status": "existing" | "created" }
```

**Example:**

```bash
curl -X POST http://localhost:23373/v1/chats \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
        "accountID": "local-whatsapp_ba_...",
        "mode": "create",
        "type": "single",
        "participantIDs": ["ba_..."]
      }'
```

### `GET /v1/chats/{chatID}`
*(Replaces `GET /v0/get-chat`.)*

Retrieve a single chat's metadata, participants, and last-activity info.

**Path params:** `chatID` (required). Not available for iMessage chats.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `maxParticipantCount` | integer | `20` | `-1` for all; otherwise `0–500`. If truncated, `participants.hasMore = true` |

**Response 200:** `Chat` object (see `schemas.md`).

### `GET /v1/chats/search`
*(Replaces `GET /v0/search-chats`.)*

Search chats by title, network, or participants. Cursor-paginated.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `query` | string | — | Literal word matching (not semantic). All words must match. |
| `scope` | `"titles"` \| `"participants"` | `"titles"` | Where to match |
| `inbox` | `"primary"` \| `"low-priority"` \| `"archive"` | — | Restrict to one inbox |
| `type` | `"single"` \| `"group"` \| `"any"` | — | Chat type filter |
| `limit` | integer | `50` | Range `1–200` |
| `cursor` | string | — | Opaque pagination cursor |
| `direction` | `"before"` \| `"after"` | `"before"` | |
| `unreadOnly` | boolean | — | Only unread |
| `accountIDs` | string[] | — | Restrict to specific accounts |
| `includeMuted` | boolean | `true` | Set `false` to exclude muted |
| `lastActivityBefore` | ISO 8601 | — | Exclusive upper bound |
| `lastActivityAfter` | ISO 8601 | — | Exclusive lower bound |

**Response 200:** paginated `Chat` objects with `oldestCursor`, `newestCursor`, `hasMore`.

### `POST /v1/chats/{chatID}/archive`
*(Replaces `POST /v0/archive-chat`.)*

Archive or unarchive a chat.

**Path params:** `chatID`.

**Body:**

| Field | Type | Default | Notes |
|---|---|---|---|
| `archived` | boolean | `true` | `true` → archive, `false` → unarchive |

**Response 200:**

```json
{ "success": true }
```

**Example:**

```bash
curl -X POST http://localhost:23373/v1/chats/$CHAT_ID/archive \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{ "archived": true }'
```

---

## Messages

### `GET /v1/chats/{chatID}/messages`

List messages in a chat, sorted by timestamp, cursor-paginated.

**Path params:** `chatID`.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `cursor` | string | — | Opaque cursor |
| `direction` | `"before"` \| `"after"` | `"before"` | `before` fetches older |
| `limit` | integer | — | Page size |

**Response 200:** array of `Message` objects (see `schemas.md`). Response also carries `oldestCursor`, `newestCursor`, `hasMore`.

**Example (curl, tail of chat):**

```bash
curl "http://localhost:23373/v1/chats/$CHAT_ID/messages?limit=50" \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

### `POST /v1/chats/{chatID}/messages`
*(Replaces `POST /v0/send-message`.)*

Send a text message, attachment, or reply. Returns a `pendingMessageID`.

**Path params:** `chatID`.

**Request body:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `text` | string | no | Message content; markdown supported. Either `text` or `attachment` must be provided. |
| `replyToMessageID` | string | no | Existing message ID to reply to |
| `attachment` | object | no | Attachment payload — see below |

**Attachment object:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `uploadID` | string | yes | From `POST /v1/assets/upload` or `/upload/base64` |
| `fileName` | string | no | |
| `mimeType` | string | no | e.g. `image/png` |
| `duration` | number | no | Seconds (audio/video) |
| `size` | `{ width: number, height: number }` | no | Pixel dimensions |
| `type` | `"gif"` \| `"voiceNote"` \| `"sticker"` | no | Special attachment type |

**Response 200:**

```json
{
  "success": true,
  "chatID": "!signal_adamvy:local-signal.localhost",
  "pendingMessageID": "m1694783291234567"
}
```

**Example (text + reply):**

```bash
curl -X POST http://localhost:23373/v1/chats/$CHAT_ID/messages \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
        "text": "Got it, on my way",
        "replyToMessageID": "m1694783291234567"
      }'
```

**Example (image attachment):**

```bash
# Step 1: upload the asset
UPLOAD=$(curl -s -X POST http://localhost:23373/v1/assets/upload \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -F 'file=@/path/to/photo.jpg')
UPLOAD_ID=$(echo "$UPLOAD" | jq -r '.uploadID')

# Step 2: send message referencing uploadID
curl -X POST http://localhost:23373/v1/chats/$CHAT_ID/messages \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
        \"text\": \"Photo attached\",
        \"attachment\": { \"uploadID\": \"$UPLOAD_ID\", \"mimeType\": \"image/jpeg\" }
      }"
```

### `PUT /v1/chats/{chatID}/messages/{messageID}`

Edit an existing message's text. **Messages with attachments cannot be edited.**

**Path params:** `chatID`, `messageID`.

**Request body:**

| Field | Type | Required |
|---|---|---|
| `text` | string | yes |

**Response 200:**

```json
{ "success": true, "chatID": "...", "messageID": "..." }
```

**Example:**

```bash
curl -X PUT http://localhost:23373/v1/chats/$CHAT_ID/messages/$MESSAGE_ID \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{ "text": "corrected text" }'
```

### `GET /v1/messages/search`
*(Replaces `GET /v0/search-messages`.)*

Full-text search across messages on the local index, with powerful filters. Cursor-paginated.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `query` | string | — | **Literal** word matching (NOT semantic). Exact word matches in any order. |
| `chatIDs` | string[] | — | Restrict to specific Beeper chat IDs |
| `accountIDs` | string[] | — | Restrict to specific bridge instances |
| `chatType` | `"group"` \| `"single"` | — | Filter |
| `mediaTypes` | array of `"any"` \| `"video"` \| `"image"` \| `"link"` \| `"file"` | — | Attachment type filter; omit for no media filtering |
| `sender` | `"me"` \| `"others"` \| userID | — | Sender filter |
| `dateBefore` | ISO 8601 | — | Strict upper bound |
| `dateAfter` | ISO 8601 | — | Strict lower bound |
| `limit` | integer | `20` | `1–500`, implementation caps at `20` |
| `cursor` | string | — | Opaque |
| `direction` | `"before"` \| `"after"` | `"before"` | |
| `excludeLowPriority` | boolean | `true` | |
| `includeMuted` | boolean | `true` | |

**Response 200:**

```ts
{
  items: Message[];
  chats: Record<string, Chat>; // referenced chats keyed by chatID
  hasMore: boolean;
  oldestCursor: string | null;
  newestCursor: string | null;
}
```

**Example (recent mentions of "invoice" from others):**

```bash
curl "http://localhost:23373/v1/messages/search?query=invoice&sender=others&dateAfter=2026-03-01T00:00:00Z" \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

**Example (images in a specific chat):**

```bash
curl "http://localhost:23373/v1/messages/search?mediaTypes=image&chatIDs=!NCdzlIaMjZUmvmvyHU:beeper.com" \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

**Example (paginate older results):**

```bash
curl "http://localhost:23373/v1/messages/search?query=meeting&cursor=$OLDEST_CURSOR&direction=before" \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

---

## Reactions

### `POST /v1/chats/{chatID}/messages/{messageID}/reactions`

Add a reaction to an existing message.

**Path params:** `chatID`, `messageID`.

**Request body:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `reactionKey` | string | yes | Emoji character, shortcode, or network-specific key |
| `transactionID` | string | no | Client-generated dedup ID for retry safety |

**Response 200:**

```json
{
  "success": true,
  "chatID": "...",
  "messageID": "...",
  "reactionKey": "👍",
  "transactionID": "..."
}
```

### `DELETE /v1/chats/{chatID}/messages/{messageID}/reactions`

Remove the authenticated user's reaction.

**Path params:** `chatID`, `messageID`.

**Query params:**

| Param | Type | Required | Notes |
|---|---|---|---|
| `reactionKey` | string | yes | Same key used when adding |

**Response 200:**

```json
{ "success": true, "chatID": "...", "messageID": "...", "reactionKey": "👍" }
```

---

## Reminders

### `POST /v1/chats/{chatID}/reminders`
*(Replaces `POST /v0/set-chat-reminder`.)*

Set a reminder on a chat at a specific Unix time.

**Request body:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `reminder.remindAtMs` | number | yes | Unix ms timestamp |
| `reminder.dismissOnIncomingMessage` | boolean | no | Cancel reminder if a new message arrives first |

**Response 200:**

```json
{ "success": true }
```

**Example:**

```bash
curl -X POST http://localhost:23373/v1/chats/$CHAT_ID/reminders \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
        "reminder": {
          "remindAtMs": 1767225600000,
          "dismissOnIncomingMessage": true
        }
      }'
```

### `DELETE /v1/chats/{chatID}/reminders`
*(Replaces `POST /v0/clear-chat-reminder`.)*

Clear any existing reminder on a chat.

**Response 200:**

```json
{ "success": true }
```

---

## Contacts

### `GET /v1/accounts/{accountID}/contacts`
*(Replaces `GET /v0/search-users`.)*

Search contacts on a single account. Combines merged local contacts, network search, and exact identifier lookup.

**Path params:** `accountID`.

**Query params:**

| Param | Type | Required | Notes |
|---|---|---|---|
| `query` | string | yes | ≥1 char; network-specific behavior |

**Response 200:**

```ts
{
  items: {
    id: string;
    username?: string;
    phoneNumber?: string;
    email?: string;
    fullName?: string;
    imgURL?: string;
    cannotMessage?: boolean;
    isSelf?: boolean;
  }[];
}
```

### `GET /v1/accounts/{accountID}/contacts/list`

List all merged contacts on one account with cursor pagination.

**Query params:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `query` | string | — | Optional narrowing |
| `limit` | integer | — | |
| `cursor` | string | — | Opaque |
| `direction` | `"before"` \| `"after"` | `"before"` | |

**Response 200:** paginated `Participant` objects (same shape as the single-item in the search response above).

---

## Search

### `GET /v1/search`
*(Replaces `GET /v0/search`.)*

One-shot unified search. Returns matching chats, in-group participant matches, and the first page of matching messages in a single response. To paginate deeper, call `/v1/chats/search` or `/v1/messages/search` with the filters that match the original query.

**Query params:**

| Param | Type | Required |
|---|---|---|
| `query` | string (≥1 char) | yes |

**Response 200:**

```ts
{
  results: {
    chats: Chat[];
    in_groups: object[];        // chats where participant name matched
    messages: {
      items: Message[];
      chats: Record<string, Chat>;
      hasMore: boolean;
      oldestCursor: string | null;
      newestCursor: string | null;
    };
  };
}
```

**Example:**

```bash
curl "http://localhost:23373/v1/search?query=payroll" \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

---

## Assets

Beeper stores chat attachments as Matrix `mxc://` or local `localmxc://` URLs. These are opaque — use the endpoints below to convert them into something readable.

### `GET /v1/assets/serve`

Stream a file given an `mxc://`, `localmxc://`, or `file://` URL. Downloads first if not yet cached. **Supports HTTP Range requests** — ideal for media playback and seek.

**Query params:**

| Param | Type | Required |
|---|---|---|
| `url` | string | yes |

**Example (seek the first 1 MB of a video):**

```bash
curl -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
     -H "Range: bytes=0-1048575" \
     "http://localhost:23373/v1/assets/serve?url=$ENCODED_MXC" \
     -o preview.bin
```

### `POST /v1/assets/download`
*(Replaces `POST /v0/download-asset`.)*

Download a Matrix asset to the local device and return the local `file://` URL.

**Body:**

| Field | Type | Required |
|---|---|---|
| `url` | string | yes — must be `mxc://` or `localmxc://` |

**Response 200:**

```json
{ "srcURL": "file:///tmp/beeper/..." }
```

On failure: `{ "error": "..." }`.

### `POST /v1/assets/upload`

Upload a file using `multipart/form-data`. Returns an `uploadID` to reference in `POST /v1/chats/{chatID}/messages`.

**Form fields:**

| Field | Type | Required |
|---|---|---|
| `file` | file | yes |
| `fileName` | string | no |
| `mimeType` | string | no |

**Response 200:**

```ts
{
  uploadID: string;
  srcURL?: string;
  fileName?: string;
  fileSize?: number;
  mimeType?: string;
  width?: number;
  height?: number;
  duration?: number;
  error?: string;
}
```

**Example:**

```bash
curl -X POST http://localhost:23373/v1/assets/upload \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -F 'file=@/path/to/photo.jpg' \
  -F 'fileName=photo.jpg' \
  -F 'mimeType=image/jpeg'
```

### `POST /v1/assets/upload/base64`

Alternative to multipart upload that accepts base64-encoded content in JSON. Use when multipart is inconvenient (e.g. browser `fetch` to a local server, certain sandboxes).

**Body:**

| Field | Type | Required |
|---|---|---|
| `content` | string | yes — base64-encoded file content |
| `fileName` | string | no |
| `mimeType` | string | no |

**Response 200:** same shape as `/v1/assets/upload`.

**Example:**

```bash
B64=$(base64 -w0 /path/to/photo.jpg)
curl -X POST http://localhost:23373/v1/assets/upload/base64 \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{ \"content\": \"$B64\", \"fileName\": \"photo.jpg\", \"mimeType\": \"image/jpeg\" }"
```

---

## App control

### `POST /v1/focus`
*(Replaces `POST /v0/open-app`.)*

Brings the Beeper Desktop window to the foreground. Optionally navigates to a chat, jumps to a specific message, and pre-fills a draft (text and/or attachment).

**Body:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `chatID` | string | no | Target chat to focus |
| `messageID` | string | no | Jump to a specific message in the focused chat |
| `draftText` | string | no | Pre-fill the composer |
| `draftAttachmentPath` | string | no | Pre-fill the composer attachment |

**Response 200:**

```json
{ "success": true }
```

**Example (just focus the window):**

```bash
curl -X POST http://localhost:23373/v1/focus \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

**Example (open chat with a draft):**

```bash
curl -X POST http://localhost:23373/v1/focus \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
        "chatID": "!NCdzlIaMjZUmvmvyHU:beeper.com",
        "draftText": "Sending in 1 min…"
      }'
```

---

## OAuth

### `GET /.well-known/oauth-authorization-server`

RFC 8414 OAuth 2.0 authorization server metadata. Use this for PKCE flows and endpoint discovery. See `references/authentication.md`.

### `POST /oauth/introspect`

Validate a token.

**Headers:** `Content-Type: application/x-www-form-urlencoded`
**Body:** `token=<your_token>&token_type_hint=access_token`

**Response 200:**

```json
{ "active": true, "scope": "...", "client_id": "...", "exp": 1767225600 }
```

or

```json
{ "active": false }
```

---

## Cross-reference: deprecated `/v0` → current `/v1`

| `/v0` (deprecated) | `/v1` (current) |
|---|---|
| `GET /v0/get-accounts` | `GET /v1/accounts` |
| `GET /v0/search-users` | `GET /v1/accounts/{accountID}/contacts` |
| `GET /v0/get-chat` | `GET /v1/chats/{chatID}` |
| `GET /v0/search-chats` | `GET /v1/chats/search` |
| `POST /v0/create-chat` | `POST /v1/chats` |
| `POST /v0/archive-chat` | `POST /v1/chats/{chatID}/archive` |
| `POST /v0/set-chat-reminder` | `POST /v1/chats/{chatID}/reminders` |
| `POST /v0/clear-chat-reminder` | `DELETE /v1/chats/{chatID}/reminders` |
| `GET /v0/search-messages` | `GET /v1/messages/search` |
| `POST /v0/send-message` | `POST /v1/chats/{chatID}/messages` |
| `GET /v0/search` | `GET /v1/search` |
| `POST /v0/download-attachment` | `POST /v1/assets/download` |
| `POST /v0/download-asset` | `POST /v1/assets/download` |
| `POST /v0/open-app` | `POST /v1/focus` |
