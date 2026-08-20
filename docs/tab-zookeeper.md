# ZooKeeper Tab

The **ZooKeeper** tab lists the routes Traefik reads from its ZooKeeper KV provider.

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the ZooKeeper provider, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel.

Routes are **read-only** - edit them directly in your ZooKeeper instance.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → ZooKeeper |
| Later | Settings → Route Monitoring → ZooKeeper |

## Requirements

Traefik must be configured with the ZooKeeper provider in your `traefik.yml`:

```yaml
providers:
  zooKeeper:
    endpoints:
      - "zookeeper:2181"
```

No mounts into traefik-manager needed - data comes live from the Traefik API.
