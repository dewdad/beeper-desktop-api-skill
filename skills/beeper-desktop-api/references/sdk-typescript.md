# TypeScript SDK: `@beeper/desktop-api`

Official TypeScript/JavaScript SDK for the Beeper Desktop API. Works in Node.js, browsers (with CORS enabled on the server), Deno, Bun, and Cloudflare Workers.

## Install

```bash
npm install @beeper/desktop-api
# or
pnpm add @beeper/desktop-api
# or
yarn add @beeper/desktop-api
```

## Initialization

```ts
import BeeperDesktop from '@beeper/desktop-api';

const client = new BeeperDesktop({
  accessToken: process.env['BEEPER_ACCESS_TOKEN'], // defaults to BEEPER_ACCESS_TOKEN env var
});
```

### Client options

| Option | Type | Default | Description |
|---|---|---|---|
| `accessToken` | `string` | `process.env.BEEPER_ACCESS_TOKEN` | Bearer token. |
| `baseURL` | `string` | `http://localhost:23373` | Override the server URL. |
| `maxRetries` | `number` | `2` | Automatic retries on 408/409/429/5xx with exponential backoff. |
| `timeout` | `number` | `60000` | Per-request timeout in ms. |
| `logLevel` | `'off' \| 'error' \| 'warn' \| 'info' \| 'debug'` | `'warn'` | Logging verbosity. |
| `logger` | `Logger` | console-based | Custom logger (methods: `error`, `warn`, `info`, `debug`). |
| `fetch` | `typeof fetch` | global `fetch` | Custom fetch implementation. |
| `fetchOptions` | `RequestInit` | — | Additional fetch options merged into every request (proxies, agents, etc.). |

Environment variable: `BEEPER_ACCESS_TOKEN` is read automatically if `accessToken` is omitted.

## Method reference

Every method returns a Promise (or a paginated async iterable where noted). All IDs are strings.

### `client.info`

| Method | Description |
|---|---|
| `client.info.retrieve()` | App/platform/server/endpoints metadata (versions, OAuth + WebSocket URLs). |

### `client.accounts`

| Method | Description |
|---|---|
| `client.accounts.list()` | Array of connected accounts (one per connected network). |
| `client.accounts.contacts.list(accountID, { cursor?, direction?, limit?, query? })` | Paginated `Participant[]` for an account's address book. |
| `client.accounts.contacts.search(accountID, { query })` | `{ items: Participant[] }` — non-paginated substring search. |

### `client.chats`

| Method | Description |
|---|---|
| `client.chats.list({ accountIDs?, cursor?, direction? })` | Paginated chats. Each item includes a `preview` (latest `Message`). |
| `client.chats.retrieve(chatID, { maxParticipantCount? })` | Single `Chat`. |
| `client.chats.create({ accountID, mode?, type?, participantIDs?, title?, messageText?, allowInvite?, user? })` | Create (`mode: 'create'`) or start (`mode: 'start'`) a chat. `type`: `'single'` or `'group'`. Returns `{ chatID, status?: 'existing' \| 'created' }`. |
| `client.chats.search({ query?, scope?, inbox?, type?, limit?, cursor?, direction?, unreadOnly?, accountIDs?, includeMuted?, lastActivityBefore?, lastActivityAfter? })` | Paginated `Chat[]`. |
| `client.chats.archive(chatID, { archived? })` | Archive (`true`) or unarchive (`false`). |
| `client.chats.reminders.create(chatID, { reminder: { remindAtMs, dismissOnIncomingMessage? } })` | Create a reminder for a chat. |
| `client.chats.reminders.delete(chatID)` | Clear a chat reminder. |
| `client.chats.messages.reactions.add(messageID, { chatID, reactionKey, transactionID? })` | Add a reaction (emoji or protocol-specific key). |
| `client.chats.messages.reactions.delete(messageID, { chatID, reactionKey })` | Remove a reaction. |

### `client.messages`

| Method | Description |
|---|---|
| `client.messages.list(chatID, { cursor?, direction? })` | Paginated `Message[]` for a chat (newest first by default). |
| `client.messages.send(chatID, { text?, replyToMessageID?, attachment? })` | Send a message. `attachment` shape: `{ uploadID, fileName?, mimeType?, duration?, size?, type? }`. Returns `{ chatID, pendingMessageID }`. |
| `client.messages.update(messageID, { chatID, text })` | Edit text. Returns `{ chatID, messageID, success }`. Text-only — fails on messages with attachments. |
| `client.messages.search({ query?, chatIDs?, accountIDs?, chatType?, mediaTypes?, sender?, dateAfter?, dateBefore?, limit?, cursor?, direction?, excludeLowPriority?, includeMuted? })` | Paginated cross-chat `Message[]`. |

### `client.search` (top-level unified search)

| Method | Description |
|---|---|
| `client.search({ query })` | Unified results: `{ chats, inGroups, messages }`. `messages` is a single page (not auto-paginated). |

### `client.focus`

| Method | Description |
|---|---|
| `client.focus({ chatID?, messageID?, draftText?, draftAttachmentPath? })` | Focuses Beeper Desktop. If `chatID` is provided, opens that chat; optional `draftText` pre-fills the composer. |

### `client.assets`

| Method | Description |
|---|---|
| `client.assets.upload({ file, fileName?, mimeType? })` | Multipart upload. `file` accepts `fs.ReadStream`, a `File`, a `fetch` `Response`, or the result of `toFile()` (imported from `@beeper/desktop-api/uploads`). Returns `{ uploadID, srcURL?, fileName?, fileSize?, mimeType?, width?, height?, duration?, error? }`. |
| `client.assets.uploadBase64({ content, fileName?, mimeType? })` | JSON base64 upload. Same response shape. |
| `client.assets.download({ url })` | Downloads a `mxc://` / `localmxc://` URL to a local file. Returns `{ srcURL?, error? }`. |
| `client.assets.serve({ url })` | Streams raw bytes (returns a `Response` — call `.arrayBuffer()`, `.blob()`, or pipe `.body`). |

## Auto-pagination

List/search methods return pagination helpers. Iterate directly with `for await`:

```ts
for await (const msg of client.messages.search({ query: 'invoice' })) {
  console.log(msg.senderName, msg.text);
}
```

Or advance pages manually:

```ts
let page = await client.messages.search({ query: 'invoice' });
while (true) {
  for (const msg of page.items) { /* ... */ }
  if (!page.hasNextPage()) break;
  page = await page.getNextPage();
}
```

## Error handling

All HTTP errors subclass `BeeperDesktop.APIError`:

| Class | Status | Typical cause |
|---|---|---|
| `BadRequestError` | 400 | Malformed params. |
| `AuthenticationError` | 401 | Missing/invalid token. |
| `PermissionDeniedError` | 403 | Token scope insufficient. |
| `NotFoundError` | 404 | Chat/message/account not found. |
| `UnprocessableEntityError` | 422 | Validation failed. |
| `RateLimitError` | 429 | Too many requests — SDK retries if `maxRetries > 0`. |
| `InternalServerError` | 5xx | Server-side failure — retried automatically. |
| `APIConnectionError` | — | Network error (DNS, reset, timeout). |

```ts
import BeeperDesktop from '@beeper/desktop-api';

try {
  await client.messages.send(chatID, { text: 'hi' });
} catch (err) {
  if (err instanceof BeeperDesktop.APIError) {
    console.error(err.status, err.name, err.message, err.headers);
  } else {
    throw err;
  }
}
```

## Raw response access

Every method has `.asResponse()` and `.withResponse()` variants:

```ts
const resp = await client.accounts.list().asResponse();
console.log(resp.headers.get('x-request-id'));

const { data, response } = await client.accounts.list().withResponse();
```

## Escape hatch — undocumented endpoints

```ts
// Call any path directly while still benefiting from auth, retries, logging.
const result = await client.post('/some/experimental/path', {
  body: { foo: 'bar' },
  query: { limit: 10 },
});
```

Also available: `client.get`, `client.put`, `client.delete`, `client.patch`.

## End-to-end example

```ts
import BeeperDesktop from '@beeper/desktop-api';

const client = new BeeperDesktop({ accessToken: process.env.BEEPER_ACCESS_TOKEN });

async function main() {
  // 1. Who am I connected to?
  const accounts = await client.accounts.list();
  console.log(`Connected to ${accounts.length} networks`);

  // 2. Find recent messages mentioning "invoice"
  const matches: string[] = [];
  for await (const msg of client.messages.search({ query: 'invoice', limit: 20 })) {
    matches.push(`${msg.senderName}: ${msg.text}`);
  }
  console.log(matches.join('\n'));

  // 3. Reply to the newest one
  if (matches.length) {
    const newest = (await client.messages.search({ query: 'invoice', limit: 1 })).items[0];
    await client.messages.send(newest.chatID, {
      text: 'Thanks — will process shortly.',
      replyToMessageID: newest.messageID,
    });
  }
}

main().catch(console.error);
```
