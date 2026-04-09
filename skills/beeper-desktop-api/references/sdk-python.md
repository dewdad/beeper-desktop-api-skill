# Python SDK: `beeper_desktop_api`

Official Python SDK for the Beeper Desktop API. Ships both sync (`BeeperDesktop`) and async (`AsyncBeeperDesktop`) clients. Type hints throughout, Pydantic models for responses.

## Install

```bash
pip install git+ssh://git@github.com/beeper/desktop-api-python.git
```

Optional aiohttp backend:

```bash
pip install "beeper_desktop_api[aiohttp] @ git+ssh://git@github.com/beeper/desktop-api-python.git"
```

## Initialization

### Sync

```python
from beeper_desktop_api import BeeperDesktop

client = BeeperDesktop(
    access_token="your_token_here",   # or set BEEPER_ACCESS_TOKEN
    max_retries=2,                     # default 2
    timeout=30.0,                      # default 60
)
```

### Async

```python
import asyncio
from beeper_desktop_api import AsyncBeeperDesktop

client = AsyncBeeperDesktop(access_token="your_token_here")
```

Environment variable: `BEEPER_ACCESS_TOKEN` is read automatically.

## Method reference

All parameters are snake_case. Method signatures are identical between sync and async clients — the async versions are coroutines.

### `client.info`

| Method | Description |
|---|---|
| `client.info.retrieve()` | Server/app metadata. |

### `client.accounts`

| Method | Description |
|---|---|
| `client.accounts.list()` | Connected accounts. |
| `client.accounts.contacts.list(account_id, query=None, cursor=None, direction=None, limit=None)` | Paginated contact list. |
| `client.accounts.contacts.search(account_id, query=...)` | Substring contact search. |

### `client.chats`

| Method | Description |
|---|---|
| `client.chats.list(account_ids=None, cursor=None, direction=None)` | Paginated chats (with `preview`). |
| `client.chats.retrieve(chat_id, max_participant_count=None)` | Single chat. |
| `client.chats.create(account_id=..., mode=None, type=None, participant_ids=None, title=None, message_text=None, allow_invite=None, user=None)` | Create or start a chat. `mode`: `'create'` or `'start'`. `type`: `'single'` or `'group'`. |
| `client.chats.search(query=None, scope=None, inbox=None, type=None, limit=None, cursor=None, direction=None, unread_only=None, account_ids=None, include_muted=None, last_activity_before=None, last_activity_after=None)` | Paginated chat search. |
| `client.chats.archive(chat_id, archived=True)` | Archive/unarchive. |
| `client.chats.reminders.create(chat_id, reminder={'remindAtMs': ..., 'dismissOnIncomingMessage': ...})` | Create chat reminder. |
| `client.chats.reminders.delete(chat_id)` | Clear chat reminder. |
| `client.chats.messages.reactions.add(message_id, chat_id=..., reaction_key=..., transaction_id=None)` | Add a reaction. |
| `client.chats.messages.reactions.delete(message_id, chat_id=..., reaction_key=...)` | Remove a reaction. |

### `client.messages`

| Method | Description |
|---|---|
| `client.messages.list(chat_id, cursor=None, direction=None)` | Paginated message list. |
| `client.messages.send(chat_id, body={...})` | Send. `body = {'text': ..., 'reply_to_message_id': ..., 'attachment': {...}}`. |
| `client.messages.update(message_id, chat_id=..., text=...)` | Edit message text. |
| `client.messages.search(query=None, chat_ids=None, account_ids=None, chat_type=None, media_types=None, sender=None, date_after=None, date_before=None, limit=None, cursor=None, direction=None, exclude_low_priority=None, include_muted=None)` | Paginated cross-chat search. |

### Top-level

| Method | Description |
|---|---|
| `client.search(query=...)` | Unified search (chats + in-groups + first page of messages). |
| `client.focus(chat_id=None, message_id=None, draft_text=None, draft_attachment_path=None)` | Focus Beeper Desktop. |

### `client.assets`

| Method | Description |
|---|---|
| `client.assets.upload(file=...)` | Multipart upload. `file` accepts `bytes`, `os.PathLike`, file-like object, or `(filename, content, content_type)` tuple. |
| `client.assets.upload_base64(content=..., file_name=None, mime_type=None)` | JSON base64 upload. |
| `client.assets.download(url=...)` | Download an `mxc://` / `localmxc://` URL to local file. |
| `client.assets.serve(url=...)` | Stream raw bytes (returns an `httpx.Response`). |

## Pagination

List methods return a paginator object that is itself iterable:

```python
# Auto-paginate
for msg in client.messages.search(query="invoice"):
    print(msg.sender_name, msg.text)

# Manual
page = client.messages.search(query="invoice")
while True:
    for msg in page.items:
        ...
    if not page.has_next_page():
        break
    page = page.get_next_page()

# Inspect cursor without fetching
info = page.next_page_info()
```

Async equivalent:

```python
async for msg in client.messages.search(query="invoice"):
    ...
```

## `with_options` — per-call overrides

Returns a shallow copy of the client with overridden options:

```python
client.with_options(max_retries=5, timeout=5.0).messages.send(chat_id, body={"text": "hi"})

# Custom httpx client (proxies, transports, etc.)
from beeper_desktop_api import DefaultHttpxClient
client.with_options(http_client=DefaultHttpxClient(proxy="http://localhost:8888"))
```

## Raw response and streaming access

```python
# Raw: get headers + deferred parse
raw = client.accounts.with_raw_response.list()
print(raw.headers.get("x-request-id"))
accounts = raw.parse()

# Streaming: context-managed, chunked
with client.accounts.with_streaming_response.list() as stream:
    for chunk in stream.iter_bytes():
        ...
```

## Escape hatch — undocumented endpoints

```python
import httpx

resp = client.post(
    "/some/experimental/path",
    cast_to=httpx.Response,
    body={"foo": "bar"},
    extra_query={"limit": "10"},
    extra_body={"flag": True},
    extra_headers={"X-Custom": "val"},
)
```

Also: `client.get`, `client.put`, `client.delete`, `client.patch`.

## Error classes

All errors inherit from `beeper_desktop_api.APIError`:

| Class | Status |
|---|---|
| `BadRequestError` | 400 |
| `AuthenticationError` | 401 |
| `PermissionDeniedError` | 403 |
| `NotFoundError` | 404 |
| `UnprocessableEntityError` | 422 |
| `RateLimitError` | 429 |
| `InternalServerError` | 5xx |
| `APIConnectionError` | network/DNS/timeout |

```python
from beeper_desktop_api import BeeperDesktop, APIError, RateLimitError

try:
    client.messages.send(chat_id, body={"text": "hi"})
except RateLimitError:
    ...  # backoff
except APIError as err:
    print(err.status_code, err.message, err.response.headers)
```

## aiohttp backend (optional)

```python
from beeper_desktop_api import AsyncBeeperDesktop, DefaultAioHttpClient

client = AsyncBeeperDesktop(
    access_token="...",
    http_client=DefaultAioHttpClient(),
)
```

## Logging

```bash
BEEPER_DESKTOP_LOG=info python my_script.py   # info
BEEPER_DESKTOP_LOG=debug python my_script.py  # debug, includes request/response bodies
```

## End-to-end (sync)

```python
import os
from beeper_desktop_api import BeeperDesktop

client = BeeperDesktop(access_token=os.environ["BEEPER_ACCESS_TOKEN"])

# 1. List connected networks
accounts = client.accounts.list()
print(f"Connected to {len(accounts)} networks")

# 2. Search messages across everything
matches = []
for msg in client.messages.search(query="invoice", limit=20):
    matches.append((msg.chat_id, msg.message_id, msg.sender_name, msg.text))

# 3. Reply to the most recent match
if matches:
    chat_id, message_id, *_ = matches[0]
    client.messages.send(
        chat_id,
        body={"text": "Thanks — will process shortly.", "reply_to_message_id": message_id},
    )
```

## End-to-end (async)

```python
import asyncio
from beeper_desktop_api import AsyncBeeperDesktop

async def main():
    client = AsyncBeeperDesktop()
    accounts = await client.accounts.list()
    print(f"Connected to {len(accounts)} networks")

    async for msg in client.messages.search(query="invoice", limit=20):
        print(msg.sender_name, msg.text)

    await client.close()

asyncio.run(main())
```
