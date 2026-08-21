# Docker Tab

The **Docker** tab lists the routes Traefik discovered through its Docker provider.

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the Docker provider, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel, which adds the container address and the route's `traefik.*` labels.

Routes are **read-only** - edit them via your container's Docker labels.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → Docker |
| Later | Settings → Route Monitoring → Docker |

## Requirements

Traefik must be configured with the Docker provider and have access to the Docker socket:

```yaml
providers:
  docker:
    exposedByDefault: false
```

With `exposedByDefault: false`, only containers labelled `traefik.enable=true` appear.

No mounts into traefik-manager needed - data comes live from the Traefik API.
