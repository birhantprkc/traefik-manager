# HTTP Provider Tab

The **HTTP Provider** tab lists the routes Traefik fetches from its HTTP provider.

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the HTTP provider, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel.

Routes are **read-only** - edit them at the endpoint Traefik polls.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → HTTP Provider |
| Later | Settings → Route Monitoring → HTTP Provider |

## Requirements

Traefik must be configured with the HTTP provider in your `traefik.yml`:

```yaml
providers:
  http:
    endpoint: "https://my-config-server/traefik-config"
    pollInterval: "5s"
```

No mounts into traefik-manager needed - data comes live from the Traefik API.
