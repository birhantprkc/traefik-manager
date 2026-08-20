# Redis Tab

The **Redis** tab lists the routes Traefik reads from its Redis KV provider.

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the Redis provider, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel.

Routes are **read-only** - edit them directly in your Redis KV store.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → Redis |
| Later | Settings → Route Monitoring → Redis |

## Requirements

Traefik must be configured with the Redis provider in your `traefik.yml`:

```yaml
providers:
  redis:
    endpoints:
      - "redis:6379"
```

No mounts into traefik-manager needed - data comes live from the Traefik API.
