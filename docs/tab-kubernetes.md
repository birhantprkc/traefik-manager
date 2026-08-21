# Kubernetes Tab

The **Kubernetes** tab lists the routes Traefik discovered through its Kubernetes providers. All three variants share one tab.

| Provider | Traefik string | Badge | Routes defined via |
|---|---|---|---|
| Kubernetes CRD | `kubernetescrd` | CRD | `IngressRoute`, `IngressRouteTCP`, `IngressRouteUDP` |
| Kubernetes Ingress | `kubernetes` | Ingress | standard `Ingress` resources |
| Kubernetes Gateway API | `kubernetesgateway` | Gateway | Gateway API resources (`HTTPRoute`, `TCPRoute`, ...) |

## What it shows

- One card per route: status, name, rule, protocol, TLS state, service, entry points, middlewares
- Provider badge, plus the namespace when the Traefik API returns one
- Summary strip: route counts per protocol, plus any route not serving
- Middlewares from the Kubernetes providers, listed under the routes
- Search, protocol filter, refresh

Click a card for its detail panel.

Routes are **read-only** - edit them via your Kubernetes manifests or Helm values.

## Enabling the tab

| Where | Path |
|---|---|
| Setup wizard | Monitoring step → Provider tabs → Kubernetes |
| Later | Settings → Route Monitoring → Kubernetes |

## Requirements

Traefik must be configured with at least one Kubernetes provider in your `traefik.yml` or Helm values. Example for CRD + Ingress:

```yaml
providers:
  kubernetesCRD: {}
  kubernetesIngress: {}
```

No mounts into traefik-manager needed - data comes live from the Traefik API.
