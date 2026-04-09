# Authentication

The Beeper Desktop API accepts a single credential type — a bearer token — across REST, WebSocket, and MCP endpoints. Tokens can be created manually in the app or via OAuth 2.0 with PKCE.

## Bearer header

Every request (REST, WebSocket handshake, MCP) uses the standard Authorization header:

```
Authorization: Bearer <your_token>
```

This applies equally to:

- REST: `http://localhost:23373/v1/*`
- WebSocket: `ws://localhost:23373/v1/ws`
- MCP: `http://localhost:23373/v0/mcp` and `http://localhost:23373/v0/sse`

## In-app token creation

Fastest path for personal scripts:

1. Open Beeper Desktop.
2. **Settings -> Developers -> Beeper Desktop API** -> enable the server.
3. **Settings -> Developers -> Approved connections -> `+`** to mint a new token.
4. Copy the token immediately — you will not be shown it again.
5. Export as `BEEPER_ACCESS_TOKEN` in your shell / CI / SDK config.

Tokens created this way are revocable from the same Approved connections screen.

## OAuth 2.0 with PKCE

For third-party apps and agent integrations, Beeper Desktop implements OAuth 2.0 (RFC 6749) with PKCE (RFC 7636).

### Discovery

```
GET /.well-known/oauth-authorization-server
```

Returns the standard RFC 8414 metadata document with the following endpoint URLs:

| Field | Purpose |
|---|---|
| `authorization_endpoint` | Browser-facing auth URL. |
| `token_endpoint` | Exchange code for token. |
| `registration_endpoint` | Dynamic client registration (RFC 7591). |
| `introspection_endpoint` | Token introspection (RFC 7662). |
| `revocation_endpoint` | Token revocation (RFC 7009). |
| `userinfo_endpoint` | User profile lookup. |

The `GET /v1/info` response also surfaces these endpoints under its `endpoints.oauth.*` keys (plus `endpoints.ws_events` for the WebSocket URL).

### Flow

1. Generate a PKCE `code_verifier` + `code_challenge`.
2. Direct the user to `authorization_endpoint` with `response_type=code`, `client_id`, `code_challenge`, `code_challenge_method=S256`, `redirect_uri`, and `scope`.
3. Exchange the returned `code` at `token_endpoint` with `grant_type=authorization_code`, `code_verifier`, and your `client_id`.
4. Use the resulting `access_token` as a bearer.

## Token introspection

```bash
curl -X POST http://localhost:23373/oauth/introspect \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=$BEEPER_ACCESS_TOKEN&token_type_hint=access_token"
```

Active token response:

```json
{
  "active": true,
  "client_id": "...",
  "scope": "...",
  "exp": 1770000000
}
```

Inactive / revoked:

```json
{ "active": false }
```

## MCP auth bypass

The MCP endpoints (`/v0/mcp` and `/v0/sse`) normally use the MCP Authorization spec's OAuth flow. If a bearer token is present on the initial request, OAuth is bypassed and the token is used directly. This is the fastest way to wire up a manually-generated token to a stdio-transport bridge or a minimal MCP client.

## CORS and remote use

The API server binds to `localhost` only. To call it from a browser-based app, enable CORS in Beeper settings or run a local reverse proxy. To call it from another machine, front it with SSH port-forwarding or a reverse proxy such as Cloudflare Tunnel — the server itself does not listen on external interfaces by default.
