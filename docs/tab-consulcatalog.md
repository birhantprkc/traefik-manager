# Consul Catalog Tab

The **Consul Catalog** tab lists the routes Traefik discovered from services registered in Consul.

> **Note:** This is the Consul *service catalog* provider (`consulcatalog`). Configuration stored in Consul's key-value store appears in the [Consul KV](tab-consul.md) tab instead.

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the Consul Catalog provider, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel.

Routes are **read-only** - edit them via your Consul service registrations and Traefik tags.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → Consul Catalog |
| Later | Settings → Route Monitoring → Consul Catalog |

## Requirements

Traefik must be configured with the Consul Catalog provider in your `traefik.yml`:

```yaml
providers:
  consulCatalog:
    endpoint:
      address: "http://localhost:8500"
```

No mounts into traefik-manager needed - data comes live from the Traefik API.
