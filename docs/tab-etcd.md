# etcd Tab

The **etcd** tab lists the routes Traefik reads from its etcd KV provider.

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the etcd provider, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel.

Routes are **read-only** - edit them directly in your etcd instance.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → etcd |
| Later | Settings → Route Monitoring → etcd |

## Requirements

Traefik must be configured with the etcd provider in your `traefik.yml`:

```yaml
providers:
  etcd:
    endpoints:
      - "etcd:2379"
```

No mounts into traefik-manager needed - data comes live from the Traefik API.
