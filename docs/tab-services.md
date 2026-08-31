# Services Tab

The **Services** tab shows all services registered in Traefik across every provider - `@file`, `@docker`, `@kubernetes`, and so on - pulled live from the Traefik API. Services from your own config files can be created and edited here; services from other providers are read only.

## What it shows

- Service name and provider (e.g. `my-app@file`, `nginx@docker`)
- Status badge: Success, Warning, or Error
- HTTP, TCP, and UDP services

## Views

Toggle between **grid** (default) and **list** view using the button in the filter bar. List view shows a compact table with Status, Protocol, Name, Backend URL, Provider, Servers, and Used By columns.

Grid view shows the service name with its type and provider below it, a status dot on the icon, its first two backend server URLs (each with a copy button, the rest behind a `+N more`), and a footer line with the server count, healthy-server ratio, and sticky or health-check flags. The number of routes using the service sits at the footer's right. Clicking the card opens the service detail panel.

## Filtering

- **Search** - service name
- **Status** - All / Success / Warnings / Errors
- **Protocol** - the protocols actually present
- **Provider** - the providers actually present

A service Traefik reports as `enabled` counts as a warning when any of its backends is not `UP`, which is what the stat panel's **backends down** count measures. Services whose status Traefik does not report at all also land in the Warnings filter, so the two counts can differ.

Composite services (`weighted`, `mirroring`, `failover`, `highestRandomWeight`) carry no backend
status of their own in Traefik - their health lives on the services they point at. They are counted
separately rather than as unchecked, and never move the backends up and down numbers.

## Creating and editing services

The **+** button in the filter bar creates a service without needing a route first. Pick a type:

| Type | Backends |
|---|---|
| Load Balancer | A list of addresses, each with its scheme |
| Weighted | Rows that are each an IP:Port or an existing service, split by weight |
| Mirroring | The first row serves; the rest receive a copy by percentage |
| Failover | The first row serves; the second takes over if it fails |

Each IP:Port row in a composite becomes its own child service named `<name>-backend-<n>`, so every
row carries its own weight. A row referencing an existing service is stored by name and never
copied, so changes to that service follow automatically. The generated children are hidden from
the list and shown on their parent's card; searching reveals them.

A `@file` service opened from its card or detail panel shows an **Edit** button. Editing keeps
settings the form does not manage - `sticky`, `healthCheck`, `service.middlewares`, mirror body
options - and only replaces what you changed. Deleting a service refuses while a route still
points at it or another service lists it as a backend.

A hand-written composite is read only until you choose **Manage this service** in its detail
panel. That records ownership without touching the file - it stays byte for byte unchanged.

## Requirements

Viewing needs no volume mounts: the list is read from the Traefik API (`/api/http/services`, `/api/tcp/services`, `/api/udp/services`), and the Traefik API URL must be configured in **Settings - Connection**.

Creating, editing and deleting write to your dynamic config files, so those need the same mount the Routes tab uses. Without it the tab still works as a read-only view.

## Notes

- This tab is always visible - it cannot be disabled
- Use the **Routes** tab to create and manage routes; a route's backend rows can reference services created here
