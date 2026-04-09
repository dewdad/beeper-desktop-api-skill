# Shared response schemas

Every Beeper Desktop API response shares a small set of object shapes. TypeScript-style interfaces below; Python/Go SDKs translate these to snake_case / PascalCase but preserve the fields.

## `Account`

Represents a connected network (one per WhatsApp/iMessage/Telegram/etc. bridge).

```ts
interface Account {
  accountID: string;        // stable, opaque — use this for routing writes
  network: string;          // display label ("WhatsApp", "Telegram", ...) — do NOT route on this
  user: {
    id: string;             // user's network-specific ID
    username?: string;
    phoneNumber?: string;
    email?: string;
    fullName?: string;
    imgURL?: string;        // avatar — may be temporary / localmxc
    cannotMessage?: boolean;
    isSelf?: boolean;
  };
}
```

**Notes.**
- `accountID` is the only field safe to persist long-term for routing. `network` strings can change between Beeper releases.
- `user.imgURL` may be `mxc://`, `localmxc://`, or `file://`. Resolve via `assets.serve` or `assets.download`.

## `Participant`

Same shape as `Account.user` but with a guaranteed `id`. Appears inside `Chat.participants` and contact lists.

```ts
interface Participant {
  id: string;
  username?: string;
  phoneNumber?: string;
  email?: string;
  fullName?: string;
  imgURL?: string;
  cannotMessage?: boolean;
  isSelf?: boolean;
}
```

## `Chat`

```ts
interface Chat {
  id: string;                    // chatID — Matrix room ID format (e.g. "!abc:beeper.com")
  accountID: string;             // owning account
  localChatID?: string;          // fallback ID for networks without durable room IDs (e.g. iMessage)
  network: string;               // display-only
  title: string;
  type: 'single' | 'group';
  participants: {
    items: Participant[];
    hasMore: boolean;
    total: number;
  };
  unreadCount: number;
  lastActivity?: number;         // unix ms
  lastReadMessageSortKey?: string;
  isArchived?: boolean;
  isMuted?: boolean;
  isPinned?: boolean;
  preview?: Message;             // set on chats.list
}
```

**Notes.**
- `id` may be absent or unstable for iMessage; prefer `localChatID` as a fallback key for local storage.
- `participants.items` is typically truncated to `maxParticipantCount` on group chats — check `hasMore` / `total`.
- `lastActivity` is unix milliseconds.

## `Message`

```ts
interface Message {
  id: string;                    // alias of messageID
  messageID: string;             // use this for edit/react/reply
  chatID: string;
  accountID: string;
  senderID: string;              // matches a Participant.id
  senderName?: string;
  sortKey: string;               // opaque — use for ordering within a chat only
  timestamp: number;             // unix ms
  text?: string;                 // body (may be empty on attachment-only messages)
  isSender?: boolean;            // true if the authenticated user sent this
  isUnread?: boolean;
  type?: string;                 // protocol-specific; e.g. "text", "sticker", "system"
  linkedMessageID?: string;      // reply target
  attachments?: Attachment[];
  reactions?: Reaction[];
}
```

**Notes.**
- `id === messageID`. Prefer `messageID` in code for clarity.
- `sortKey` is opaque and comparable only within a single chat. Do not parse or sort across chats.
- `timestamp` is unix milliseconds.
- Attachment-only messages can have empty `text`.

## `Attachment`

```ts
interface Attachment {
  type: 'unknown' | 'img' | 'video' | 'audio';
  id?: string;
  srcURL?: string;               // mxc:// | localmxc:// | file:// | https:// — may be temporary
  mimeType?: string;
  fileName?: string;
  fileSize?: number;             // bytes
  isGif?: boolean;
  isSticker?: boolean;
  isVoiceNote?: boolean;
  duration?: number;             // ms (audio/video)
  posterImg?: string;            // preview thumbnail URL
  size?: {
    width: number;
    height: number;
  };
}
```

**Notes.**
- Download `srcURL` promptly — non-HTTPS schemes are local or time-limited.
- `type: 'unknown'` means the bridge couldn't classify the file; inspect `mimeType` instead.

## `Reaction`

```ts
interface Reaction {
  id: string;
  reactionKey: string;           // canonical key ("thumbs_up" on iMessage, ":+1:" on Slack, etc.)
  participantID: string;
  emoji?: string;                // resolved emoji glyph when available
  imgURL?: string;               // for custom/image reactions
}
```

**Notes.**
- Pass `reactionKey` (not `emoji`) to `reactions.add` / `reactions.delete`.

## Paginated wrapper

All list/search endpoints wrap results in:

```ts
interface Page<T> {
  items: T[];
  hasMore: boolean;
  oldestCursor?: string;         // pass with direction='before' to go older
  newestCursor?: string;         // pass with direction='after' to go newer
}
```

**Notes.**
- Cursors are opaque. Never parse, decode, or mutate them.
- To walk oldest → newest, start with no cursor, set `direction='after'`, and loop while `hasMore`.
- SDKs (TS/Python/Go) expose async iterators that hide cursors entirely.
