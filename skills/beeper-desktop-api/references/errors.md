# Errors

All Beeper Desktop API error responses share one envelope and map cleanly to each SDK's exception hierarchy.

## Response envelope

Every non-2xx response returns JSON of the form:

```json
{
  "error": "Human-readable message",
  "code": "optional_machine_code",
  "details": {
    "field": "explanation"
  }
}
```

| Field | Type | Description |
|---|---|---|
| `error` | string | Human-readable summary. |
| `code` | string (optional) | Machine-readable identifier, e.g. `invalid_subscription`, `chat_not_found`. |
| `details` | object (optional) | Field-level validation errors keyed by field name. |

## Status code table

| Status | Meaning | Typical cause |
|---|---|---|
| 400 | Bad request | Malformed params, unknown query fields, invalid enum values. |
| 401 | Unauthorized | Missing or invalid `Authorization` header. |
| 403 | Forbidden | Token lacks the required scope. |
| 404 | Not found | chatID / messageID / accountID does not exist (or has been deleted). |
| 422 | Unprocessable entity | Validation error — fields are well-formed but semantically invalid. |
| 429 | Too many requests | Rate limit hit. Back off; SDKs auto-retry when `maxRetries > 0`. |
| 500 | Internal server error | Bridge failure, upstream network issue, bug. |
| 502 / 503 / 504 | Upstream failure | Transient — retry with backoff. |

## SDK error class mapping

| HTTP | TypeScript (`@beeper/desktop-api`) | Python (`beeper_desktop_api`) | Go (`desktop-api-go`) |
|---|---|---|---|
| 400 | `BadRequestError` | `BadRequestError` | `*Error` (inspect `StatusCode == 400`) |
| 401 | `AuthenticationError` | `AuthenticationError` | `*Error` (`StatusCode == 401`) |
| 403 | `PermissionDeniedError` | `PermissionDeniedError` | `*Error` (`StatusCode == 403`) |
| 404 | `NotFoundError` | `NotFoundError` | `*Error` (`StatusCode == 404`) |
| 422 | `UnprocessableEntityError` | `UnprocessableEntityError` | `*Error` (`StatusCode == 422`) |
| 429 | `RateLimitError` | `RateLimitError` | `*Error` (`StatusCode == 429`) |
| 5xx | `InternalServerError` | `InternalServerError` | `*Error` (`StatusCode >= 500`) |
| — | `APIConnectionError` (network) | `APIConnectionError` (network) | Go net errors |

All SDK exceptions subclass a base `APIError` with `status`, `message`, `headers`, and (where applicable) a raw response accessor.

## Retry guidance

- **429** — back off exponentially with jitter. The SDKs retry automatically up to `maxRetries` (default 2) honoring `Retry-After` if present.
- **5xx** — the same automatic retry applies; if you exhaust retries, surface the error and alert.
- **4xx (non-429)** — do NOT retry. These indicate client-side problems. Fix the request instead.
- **Network errors** — retry with backoff; they are transient and usually recover within seconds.

## Example

```ts
import BeeperDesktop from '@beeper/desktop-api';

const client = new BeeperDesktop({ maxRetries: 4 });

try {
  await client.messages.send(chatID, { text: 'hi' });
} catch (err) {
  if (err instanceof BeeperDesktop.NotFoundError) {
    console.error('Chat not found:', chatID);
  } else if (err instanceof BeeperDesktop.RateLimitError) {
    console.error('Still rate-limited after retries');
  } else if (err instanceof BeeperDesktop.APIError) {
    console.error(err.status, err.message, err.headers.get('x-request-id'));
  } else {
    throw err;
  }
}
```
