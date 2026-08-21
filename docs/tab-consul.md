# Consul KV Tab

The **Consul KV** tab lists the routes Traefik reads from its Consul KV provider.

> **Note:** This is the Consul *key-value store* provider (`consul`). Services registered in Consul's service catalog appear in the [Consul Catalog](tab-consulcatalog.md) tab instead.

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the Consul KV provider, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel.

Routes are **read-only** - edit them directly in the Consul KV store.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → Consul KV |
| Later | Settings → Route Monitoring → Consul KV |

## Requirements

Traefik must be configured with the Consul KV provider in your `traefik.yml`:

```yaml
providers:
  consul:
    endpoints:
      - "consul:8500"
```

No mounts into traefik-manager needed - data comes live from the Traefik API.
