# Remote access & tunneling

By default the Beeper Desktop API binds to `localhost:23373` only, so it is only reachable from the device running the app. Remote access makes the same API reachable from another machine — useful for agents running on a server, a phone, or a VPS.

## Enabling remote access

Open **Settings → Developers → Beeper Desktop API → Advanced settings** and flip the remote access toggle.

When remote access is enabled:

- The server binds to `0.0.0.0` (all interfaces) instead of `127.0.0.1`.
- The base URL returned by `GET /v1/info` and used in OAuth discovery is computed from the `X-Forwarded-Host` and `X-Forwarded-Proto` request headers. That means you can put the server behind a reverse proxy or tunnel and the OAuth flow + SDK auto-discovery still produce correct public URLs.

**Security implications:** anyone who can reach the port and present a valid bearer token can read and send messages on every connected network. Treat the access token like a full account credential. Prefer OAuth (per-client tokens that can be revoked individually in Settings → Developers → Approved connections) over sharing a single long-lived token.

## Cloudflare Quick Tunnels

The fastest way to expose the server is a Cloudflare Quick Tunnel — zero-config HTTPS with a random hostname:

```bash
cloudflared tunnel --url http://localhost:23373
```

Cloudflare prints a URL like `https://random-words.trycloudflare.com`. Everything the API exposes is reachable under that hostname:

- REST: `https://random-words.trycloudflare.com/v1/info`
- WebSocket: `wss://random-words.trycloudflare.com/v1/ws`
- MCP (streamable HTTP): `https://random-words.trycloudflare.com/v0/mcp`

Append the path you need. Pass the same `Authorization: Bearer <token>` header you would use locally.

### SSE is NOT supported through Cloudflare Quick Tunnels

The legacy SSE MCP transport (`/v0/sse`) does not work through Cloudflare Quick Tunnels — connections hang or drop. Use the streamable HTTP endpoint (`/v0/mcp`) instead when tunneling through Cloudflare. This is a documented limitation in Beeper's docs.

## Other reverse proxies

Any reverse proxy that sets `X-Forwarded-Host` and `X-Forwarded-Proto` will work: nginx, Caddy, Traefik, etc. Example nginx snippet:

```nginx
location / {
    proxy_pass http://127.0.0.1:23373;
    proxy_set_header Host              $host;
    proxy_set_header X-Forwarded-Host  $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_http_version 1.1;
    proxy_set_header Upgrade           $http_upgrade;
    proxy_set_header Connection        "upgrade";
}
```

The `Upgrade`/`Connection` headers are required for the `/v1/ws` WebSocket endpoint.

## Verifying the tunnel

Smoke-test the tunnel with `/v1/info` — it should echo back the public base URL it derived from the forwarding headers:

```bash
curl https://random-words.trycloudflare.com/v1/info \
  -H "Authorization: Bearer $BEEPER_ACCESS_TOKEN"
```

Inspect `.server.base_url` and `.endpoints.*` in the response — they should match the public hostname. If they still report `http://localhost:23373`, the forwarding headers aren't being passed through correctly.
