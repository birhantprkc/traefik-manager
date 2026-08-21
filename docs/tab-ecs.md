# ECS Tab

The **ECS** tab lists the routes Traefik discovered through its Amazon ECS provider.

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the ECS provider, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel.

Routes are **read-only** - edit them via your ECS task definitions and Traefik labels.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → ECS |
| Later | Settings → Route Monitoring → ECS |

## Requirements

Traefik must be configured with the ECS provider in your `traefik.yml`:

```yaml
providers:
  ecs:
    region: us-east-1
    clusters:
      - my-cluster
```

No mounts into traefik-manager needed - data comes live from the Traefik API.
