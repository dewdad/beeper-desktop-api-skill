# Go SDK: `github.com/beeper/desktop-api-go`

Official Go SDK for the Beeper Desktop API. Context-first, typed params/responses, iterator-based pagination.

## Install

```bash
go get github.com/beeper/desktop-api-go
```

## Initialization

```go
package main

import (
    "context"
    "os"

    beeperdesktopapi "github.com/beeper/desktop-api-go"
    "github.com/beeper/desktop-api-go/option"
)

func main() {
    client := beeperdesktopapi.NewClient(
        option.WithAccessToken(os.Getenv("BEEPER_ACCESS_TOKEN")),
        // option.WithBaseURL("http://localhost:23373"),
        // option.WithMaxRetries(2),
        // option.WithRequestTimeout(30 * time.Second),
    )

    ctx := context.Background()
    info, err := client.Info.Get(ctx)
    _ = info
    _ = err
}
```

Environment variable: `BEEPER_ACCESS_TOKEN` is read automatically if `option.WithAccessToken` is omitted.

## Method reference

All methods take `context.Context` as the first argument and typed params structs as the last. Return types are Go structs that mirror the REST responses.

### `client.Info`

| Method | Description |
|---|---|
| `client.Info.Get(ctx)` | Server info. |

### `client.Accounts`

| Method | Description |
|---|---|
| `client.Accounts.List(ctx)` | Connected accounts. |
| `client.Accounts.Contacts.List(ctx, accountID, params)` | Paginated contacts. |
| `client.Accounts.Contacts.Search(ctx, accountID, params)` | Substring contact search. |

### `client.Chats`

| Method | Description |
|---|---|
| `client.Chats.List(ctx, params)` | Paginated chats. |
| `client.Chats.Get(ctx, chatID, params)` | Single chat. |
| `client.Chats.New(ctx, params)` | Create or start a chat. |
| `client.Chats.Search(ctx, params)` | Paginated chat search. |
| `client.Chats.Archive(ctx, chatID, params)` | Archive/unarchive. |
| `client.Chats.Reminders.New(ctx, chatID, params)` | Create reminder. |
| `client.Chats.Reminders.Delete(ctx, chatID)` | Clear reminder. |
| `client.Chats.Messages.Reactions.New(ctx, messageID, params)` | Add reaction. |
| `client.Chats.Messages.Reactions.Delete(ctx, messageID, params)` | Remove reaction. |

### `client.Messages`

| Method | Description |
|---|---|
| `client.Messages.List(ctx, chatID, params)` | Paginated messages. |
| `client.Messages.Send(ctx, chatID, params)` | Send a message. |
| `client.Messages.Update(ctx, messageID, params)` | Edit message text. |
| `client.Messages.Search(ctx, params)` | Paginated cross-chat search. |

### Top-level

| Method | Description |
|---|---|
| `client.Search(ctx, params)` | Unified search. |
| `client.Focus(ctx, params)` | Focus Beeper Desktop. |

### `client.Assets`

| Method | Description |
|---|---|
| `client.Assets.Upload(ctx, params)` | Multipart upload. |
| `client.Assets.UploadBase64(ctx, params)` | Base64 upload. |
| `client.Assets.Download(ctx, params)` | Download mxc/localmxc URL. |
| `client.Assets.Serve(ctx, params)` | Stream raw bytes. |

## Pagination

Paginated endpoints return iterators with `.Next()` / `.Current()` / `.Err()`. The idiomatic pattern is the `AutoPager`:

```go
iter := client.Messages.Search(ctx, beeperdesktopapi.MessageSearchParams{
    Query: beeperdesktopapi.String("invoice"),
    Limit: beeperdesktopapi.Int(50),
})

for iter.Next() {
    msg := iter.Current()
    fmt.Println(msg.SenderName, msg.Text)
}
if err := iter.Err(); err != nil {
    log.Fatal(err)
}
```

Manual page walking is also supported via `.GetNextPage()`.

## Error handling

```go
import (
    "errors"

    beeperdesktopapi "github.com/beeper/desktop-api-go"
)

_, err := client.Messages.Send(ctx, chatID, params)
if err != nil {
    var apiErr *beeperdesktopapi.Error
    if errors.As(err, &apiErr) {
        fmt.Println(apiErr.StatusCode, apiErr.Message, apiErr.RequestID)
    }
    log.Fatal(err)
}
```

## End-to-end example

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    beeperdesktopapi "github.com/beeper/desktop-api-go"
    "github.com/beeper/desktop-api-go/option"
)

func main() {
    ctx := context.Background()
    client := beeperdesktopapi.NewClient(
        option.WithAccessToken(os.Getenv("BEEPER_ACCESS_TOKEN")),
    )

    // 1. List accounts
    accounts, err := client.Accounts.List(ctx)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Connected to %d networks\n", len(accounts))

    // 2. Search messages
    iter := client.Messages.Search(ctx, beeperdesktopapi.MessageSearchParams{
        Query: beeperdesktopapi.String("invoice"),
        Limit: beeperdesktopapi.Int(20),
    })

    var first *beeperdesktopapi.Message
    for iter.Next() {
        m := iter.Current()
        if first == nil {
            first = &m
        }
        fmt.Println(m.SenderName, m.Text)
    }
    if err := iter.Err(); err != nil {
        log.Fatal(err)
    }

    // 3. Reply to the first match
    if first != nil {
        _, err := client.Messages.Send(ctx, first.ChatID, beeperdesktopapi.MessageSendParams{
            Text:              beeperdesktopapi.String("Thanks — will process shortly."),
            ReplyToMessageID:  beeperdesktopapi.String(first.MessageID),
        })
        if err != nil {
            log.Fatal(err)
        }
    }
}
```
