# Cookbook

Copy-pasteable end-to-end recipes. Every recipe assumes `BEEPER_ACCESS_TOKEN` is exported and the Beeper Desktop API is enabled.

```bash
export BEEPER_ACCESS_TOKEN="your_token_here"
```

## Contents

1. [Export all messages from one chat to CSV (Python)](#1-export-all-messages-from-one-chat-to-csv-python)
2. [Find invoice images across all networks and save them locally (Python)](#2-find-invoice-images-across-all-networks-and-save-them-locally-python)
3. [Auto-reply bot on a keyword (Node/TypeScript)](#3-auto-reply-bot-on-a-keyword-nodetypescript)
4. [Bulk DM contacts from a CSV (Python)](#4-bulk-dm-contacts-from-a-csv-python)
5. [Cross-network unified search from the CLI (bash + curl)](#5-cross-network-unified-search-from-the-cli-bash--curl)
6. [Daily unread digest (Python)](#6-daily-unread-digest-python)
7. [Focus Beeper with a pre-filled draft (curl)](#7-focus-beeper-with-a-pre-filled-draft-curl)
8. [Watch one chat via WebSocket (Node)](#8-watch-one-chat-via-websocket-node)
9. [Send an image attachment (two-step curl)](#9-send-an-image-attachment-two-step-curl)
10. [Paginate through all chats oldest → newest (Python)](#10-paginate-through-all-chats-oldest---newest-python)

---

## 1. Export all messages from one chat to CSV (Python)

**Prerequisites.** `pip install beeper_desktop_api ...`. Know the target `chat_id`.

```python
import csv
import os
from beeper_desktop_api import BeeperDesktop

client = BeeperDesktop(access_token=os.environ["BEEPER_ACCESS_TOKEN"])
CHAT_ID = "!NCdzlIaMjZUmvmvyHU:beeper.com"

with open("chat_export.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["timestamp", "sender_id", "sender_name", "text", "message_id"])
    for msg in client.messages.list(CHAT_ID):  # auto-paginates all pages
        w.writerow([
            msg.timestamp,
            msg.sender_id,
            msg.sender_name or "",
            (msg.text or "").replace("\n", " "),
            msg.message_id,
        ])

print("Exported to chat_export.csv")
```

**Output.** A CSV with one row per message in the chat.

---

## 2. Find invoice images across all networks and save them locally (Python)

**Prerequisites.** Python SDK. Writable `./invoices/` directory.

```python
import os
import shutil
import urllib.parse
from pathlib import Path
from beeper_desktop_api import BeeperDesktop

client = BeeperDesktop(access_token=os.environ["BEEPER_ACCESS_TOKEN"])
Path("invoices").mkdir(exist_ok=True)

for msg in client.messages.search(query="invoice", media_types=["image"], limit=100):
    for att in (msg.attachments or []):
        if not att.src_url:
            continue
        # Ensure Beeper has materialized the file on disk
        dl = client.assets.download(url=att.src_url)
        local = dl.src_url  # file:// URL
        if not local or not local.startswith("file://"):
            continue
        src_path = urllib.parse.unquote(local.replace("file://", "", 1))
        dest = Path("invoices") / (att.file_name or f"{msg.message_id}.bin")
        shutil.copy(src_path, dest)
        print(f"saved {dest}")
```

**Output.** Matching images copied into `./invoices/`.

---

## 3. Auto-reply bot on a keyword (Node/TypeScript)

**Prerequisites.** `npm install @beeper/desktop-api ws`. Bot listens on all chats.

```ts
import WebSocket from 'ws';
import BeeperDesktop from '@beeper/desktop-api';

const TRIGGER = /^!ping\b/i;
const REPLY = 'pong';

const client = new BeeperDesktop({ accessToken: process.env.BEEPER_ACCESS_TOKEN });
const ws = new WebSocket('ws://localhost:23373/v1/ws', {
  headers: { Authorization: `Bearer ${process.env.BEEPER_ACCESS_TOKEN}` },
});

ws.on('message', async (buf) => {
  const evt = JSON.parse(buf.toString());
  if (evt.type === 'ready') {
    ws.send(JSON.stringify({ type: 'subscriptions.set', requestID: '1', chatIDs: ['*'] }));
    return;
  }
  if (evt.type !== 'message.upserted') return;
  for (const m of evt.entries ?? []) {
    if (m.isSender) continue;
    if (TRIGGER.test(m.text ?? '')) {
      await client.messages.send(m.chatID, { text: REPLY, replyToMessageID: m.messageID });
    }
  }
});
```

**Output.** Console-free daemon that replies `pong` to any incoming `!ping`.

---

## 4. Bulk DM contacts from a CSV (Python)

**Prerequisites.** `contacts.csv` with columns `account_id,user,body`.

```python
import csv
import os
import time
from beeper_desktop_api import BeeperDesktop, RateLimitError

client = BeeperDesktop(access_token=os.environ["BEEPER_ACCESS_TOKEN"])

with open("contacts.csv", newline="") as f:
    for row in csv.DictReader(f):
        try:
            created = client.chats.create(
                account_id=row["account_id"],
                mode="start",
                type="single",
                user=row["user"],  # phone, username, email — bridge-specific
            )
            client.messages.send(created.chat_id, body={"text": row["body"]})
            print("sent to", row["user"])
        except RateLimitError:
            time.sleep(5)
        time.sleep(0.25)  # polite pacing
```

**Output.** One DM per row. Errors logged, rate limits respected.

---

## 5. Cross-network unified search from the CLI (bash + curl)

**Prerequisites.** `curl`, `jq`.

```bash
curl -s "http://localhost:23373/v1/search?query=invoice%20march" \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  | jq '{
      chats: [.chats[] | {id, title, network: .accountID}],
      messages: [.messages.items[] | {chatID, sender: .senderName, text}]
    }'
```

**Output.** Pretty-printed JSON of chat matches and the first page of message matches.

---

## 6. Daily unread digest (Python)

**Prerequisites.** Python SDK. Run on a cron / Task Scheduler.

```python
import os
from collections import defaultdict
from beeper_desktop_api import BeeperDesktop

client = BeeperDesktop(access_token=os.environ["BEEPER_ACCESS_TOKEN"])

by_account = defaultdict(list)
for chat in client.chats.search(unread_only=True):
    by_account[chat.account_id].append(chat)

print("Daily unread digest")
print("===================")
for acct_id, chats in by_account.items():
    total = sum(c.unread_count for c in chats)
    print(f"\n{acct_id}: {len(chats)} chats, {total} unread")
    for c in chats[:10]:
        print(f"  - {c.title}: {c.unread_count}")
```

**Output.** Human-readable summary grouped by account.

---

## 7. Focus Beeper with a pre-filled draft (curl)

**Prerequisites.** `curl`.

```bash
curl -X POST http://localhost:23373/v1/focus \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "chatID": "!NCdzlIaMjZUmvmvyHU:beeper.com",
        "draftText": "Hey, just following up on the invoice."
      }'
```

**Output.** Beeper Desktop comes to the foreground with the chat open and the composer pre-filled.

---

## 8. Watch one chat via WebSocket (Node)

**Prerequisites.** `npm install ws`. Know the chat ID.

```js
import WebSocket from 'ws';

const CHAT_ID = '!NCdzlIaMjZUmvmvyHU:beeper.com';
const ws = new WebSocket('ws://localhost:23373/v1/ws', {
  headers: { Authorization: `Bearer ${process.env.BEEPER_ACCESS_TOKEN}` },
});

ws.on('message', (buf) => {
  const evt = JSON.parse(buf.toString());
  if (evt.type === 'ready') {
    ws.send(JSON.stringify({ type: 'subscriptions.set', requestID: '1', chatIDs: [CHAT_ID] }));
  } else if (evt.type === 'message.upserted') {
    for (const m of evt.entries ?? []) {
      console.log(`[${new Date(m.timestamp).toISOString()}] ${m.senderName}: ${m.text}`);
    }
  }
});
```

**Output.** Live stdout stream of new messages in the target chat.

---

## 9. Send an image attachment (two-step curl)

**Prerequisites.** `curl`, an image file (`./photo.jpg`), a target `$CHAT_ID`.

```bash
# Step 1: upload
UPLOAD_JSON=$(curl -s -X POST http://localhost:23373/v1/assets/upload \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -F "file=@./photo.jpg;type=image/jpeg")
UPLOAD_ID=$(echo "$UPLOAD_JSON" | jq -r .uploadID)

# Step 2: send a message referencing the upload
curl -X POST "http://localhost:23373/v1/chats/$CHAT_ID/messages" \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
        \"text\": \"Here's the photo\",
        \"attachment\": { \"uploadID\": \"$UPLOAD_ID\", \"fileName\": \"photo.jpg\", \"mimeType\": \"image/jpeg\" }
      }"
```

**Output.** A new message in the chat with the image attached.

---

## 10. Paginate through all chats oldest -> newest (Python)

**Prerequisites.** Python SDK.

```python
import os
from beeper_desktop_api import BeeperDesktop

client = BeeperDesktop(access_token=os.environ["BEEPER_ACCESS_TOKEN"])

page = client.chats.list(direction="after")  # start at the oldest
all_chats = []
while True:
    all_chats.extend(page.items)
    if not page.has_next_page():
        break
    page = page.get_next_page()

print(f"fetched {len(all_chats)} chats")
```

**Output.** A `list` of every chat the authenticated user has access to, oldest first.
