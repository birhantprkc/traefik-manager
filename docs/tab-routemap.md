# Route Map Tab

The **Route Map** tab shows a topology view of your Traefik routing setup: entry points to routes to middlewares to services, connected by Bezier curves.

## Enabling the tab

Enable this tab via **Settings - Interface - Tabs - Route Map**. The preference is saved to `manager.yml` and persists across restarts.

---

## Topology view

Node positions are computed by the [dagre](https://github.com/dagrejs/dagre) graph layout engine, which ranks the graph left to right into four lanes: **Entry Points - Routes - Middlewares - Services**. The map spreads to fill the available width and the curves are drawn from live DOM positions, so connections stay pixel-accurate under any filter. Curves sit above the background but below the node cards, so a route-to-service connection stays visible where it crosses the middleware lane.

Each node carries a coloured spine on its left edge:

| Node | Colour |
|--------|--------|
| Entry point | Teal |
| Route - HTTP | Blue |
| Route - TCP | Green |
| Route - UDP | Yellow |
| Middleware | Purple |
| Service | Orange |
| Provider group | Grey |

Route nodes carry a health dot from the live router state: green loaded, yellow loaded but not enabled, red errored. Service nodes take one once backend health has been read, which the Dashboard tab fetches. Disabled routes are not mapped.

**Hover** a route node to highlight its full path:
- Unrelated nodes dim
- The route, its entry point(s), middleware(s) and service take a box shadow
- A tooltip shows the route's target, entry points and middlewares

**Click** a route node to open the full route detail panel. Clicking an entry point, middleware, service or group node opens a focused popup instead:
- The background dims and a mini map appears centred on screen, using the same node styles, scoped to that node's connections
- A **details strip** below the header shows contextual information for the selected node: domain(s), target URL, protocol, TLS status, cert resolver, entry point address, or connected route count depending on node type
- Hover and click work inside the popup - hover highlights a path, click drills into any connected node
- Press **Esc** or click outside to close it

Middleware nodes show a usage count badge (e.g. `3×`) when more than one route uses them, reducing visual noise from dense curve fans.

On a phone the map pans by dragging and zooms by pinching, with zoom in, zoom out and fit-to-screen buttons in the bottom right corner.

---

## Route grouping

Routes from a non-file provider are collapsed into a single group node per provider once that provider has 6 or more routes, keeping a large Docker or Kubernetes estate readable. The node shows the provider name and the member count; clicking it opens the popup with all of its routes and their topology. File routes are always drawn individually.

---

## Filtering

| Filter | Description |
|--------|-------------|
| Search | Matches the route name |
| Protocol | Show only HTTP, TCP, or UDP routes |
| Provider | Filter by Traefik provider. The list of providers appears only when routes come from more than one |
| Entry Point | Filter to routes that use a specific entry point |

The **clear filters** button resets all four. The Entry Points lane shows only the entry points used by the routes still visible.

---

## Data source

Fetches from:

- `/api/routes/all` - routes from all providers (file-managed + live from Traefik API); `/api/agents/<id>/routes` when a remote agent is selected
- `/api/traefik/entrypoints` - entry point names from the Traefik API
- `/api/traefik/routers` - live router state for the health dots

No extra mounts or configuration required beyond a working Traefik API connection.

Data is shared with the Dashboard tab and cached for 30 seconds, so route changes made elsewhere appear without a page reload. If the Traefik API cannot be reached, the tab reports the error and retries on the next open rather than caching an empty topology.
