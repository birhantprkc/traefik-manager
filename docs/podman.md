# Running with Podman

Traefik Manager runs on Podman. This page covers the differences from Docker and the common deployment patterns.

---

## Key differences from Docker

|                     | Docker                   | Podman                                                                          |
| ---------------------| --------------------------| ---------------------------------------------------------------------------------|
| Compose command     | `docker compose`         | `podman compose` (4.7+, wraps an installed compose provider) or `podman-compose` |
| Exec into container | `docker exec`            | `podman exec`                                                                   |
| SELinux hosts       | No label needed          | Add `:z` (shared) or `:Z` (private) to volume mounts                            |
| Rootless ports      | Ports < 1024 need root   | Same - use port ≥ 1024 or configure `net.ipv4.ip_unprivileged_port_start`       |
| Restart policy      | `unless-stopped`         | Use `always` with podman-compose, or a Quadlet unit for systemd integration     |
| Network aliases     | Docker Compose sets them | Must create a named network and join both containers to it                      |

---

## podman compose

Podman 4.7+ ships the `podman compose` subcommand. On older versions install `podman-compose`:

```bash
pip install podman-compose
```

### Minimal compose file

```yaml
services:
  traefik-manager:
    image: ghcr.io/chr0nzz/traefik-manager:latest
    container_name: traefik-manager
    restart: always
    ports:
      - "5000:5000"
    environment:
      - COOKIE_SECURE=false
    volumes:
      - /path/to/traefik/dynamic.yml:/app/config/dynamic.yml:z
      - /path/to/traefik-manager/config:/app/config:z
      - /path/to/traefik-manager/backups:/app/backups:z
```

> `:z` relabels the volume for SELinux, `:Z` labels it private to this container. On non-SELinux hosts (most Debian/Ubuntu setups) the labels are harmless and can be omitted.

Start:

```bash
podman compose up -d
```

---

## Connecting to Traefik on the same host

On a shared Podman network both containers reach each other by container name.

### Create a shared network

```bash
podman network create traefik
```

### Join both containers to it

Add a `networks` block to your compose file:

```yaml
services:
  traefik-manager:
    image: ghcr.io/chr0nzz/traefik-manager:latest
    container_name: traefik-manager
    restart: always
    ports:
      - "5000:5000"
    environment:
      - COOKIE_SECURE=false
    volumes:
      - /path/to/traefik/dynamic.yml:/app/config/dynamic.yml:z
      - /path/to/traefik-manager/config:/app/config:z
      - /path/to/traefik-manager/backups:/app/backups:z
    networks:
      - traefik

networks:
  traefik:
    external: true
```

Then in the setup wizard, set the Traefik API URL to `http://traefik:8080`.

---

## Rootless Podman

Rootless Podman runs containers as your regular user with no daemon. Traefik Manager needs no extra config - run the compose commands as that user.

```bash
# Start
podman compose up -d

# First run: read the auto-generated password from the log
podman logs traefik-manager | grep -A3 AUTO-GENERATED
```

For a port below 1024, either map to a high port (`-p 8080:5000`) and put a reverse proxy in front, or lower the threshold: `sysctl -w net.ipv4.ip_unprivileged_port_start=80`.

---

## Systemd integration with Quadlet

Quadlet is the recommended way to run Podman containers as systemd services; it replaces `podman generate systemd`.

Create `/etc/containers/systemd/traefik-manager.container` (system) or `~/.config/containers/systemd/traefik-manager.container` (rootless):

```ini
[Unit]
Description=Traefik Manager
After=network-online.target

[Container]
Image=ghcr.io/chr0nzz/traefik-manager:latest
ContainerName=traefik-manager
PublishPort=5000:5000
Environment=COOKIE_SECURE=false
Volume=/path/to/traefik/dynamic.yml:/app/config/dynamic.yml:z
Volume=/path/to/traefik-manager/config:/app/config:z
Volume=/path/to/traefik-manager/backups:/app/backups:z
Network=traefik

[Service]
Restart=always

[Install]
WantedBy=default.target
```

`Network=traefik` joins the network you created with `podman network create`. A name ending in `.network` refers to a Quadlet `.network` unit instead.

Reload and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now traefik-manager
```

For system-level (root) units, drop `--user` from the systemctl commands.

---

## Password reset

```bash
podman exec traefik-manager flask reset-password
```

Prints a new temporary password and forces a change at next login. Two-factor authentication is preserved - add `--disable-otp` if you have also lost your TOTP app. Other recovery methods: [Reset Password](reset-password.md).

---

## Optional monitoring mounts

Add `:z` to every optional mount on SELinux hosts:

```yaml
volumes:
  - /path/to/traefik/acme.json:/app/acme.json:ro,z              # Certs tab
  - /path/to/traefik/traefik.yml:/app/traefik.yml:z             # Plugins + Static Config
  - /path/to/traefik/logs/access.log:/app/logs/access.log:ro,z  # Logs tab
```

Switch Certs, Plugins and Logs on in **Settings -> System Monitoring**; mounting the file alone does not reveal them. `traefik.yml` also needs `STATIC_CONFIG_PATH=/app/traefik.yml` - that path has no default.

> Mount `traefik.yml` without `:ro`. Read-only still lists plugins, but saving the static config or installing a plugin fails with a write error.

---

## Static config editor

Edit `traefik.yml` from the UI. After saving, click **Restart Traefik** to apply the change with your configured restart method.

### Requirements

Mount `traefik.yml` read-write (no `:ro`), set `STATIC_CONFIG_PATH`, and set `RESTART_METHOD`. Choose where the editor appears in **Settings -> Interface -> Tabs -> Static Config**: `Off`, `Settings` (inside the settings window) or `Tab` (its own side-nav entry).

### Method 1: Poison pill (recommended for Podman)

No socket access needed. Traefik Manager writes a signal file to a shared named volume; Traefik's own healthcheck finds it, removes it and kills itself (`kill -TERM 1`), and `restart: always` starts it again.

Add the healthcheck to your Traefik service and mount the shared volume on both containers:

```yaml
services:
  traefik:
    image: traefik:latest
    container_name: traefik
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "[ ! -f /signals/restart.sig ] || (rm /signals/restart.sig && kill -TERM 1)"]
      interval: 5s
      timeout: 3s
      retries: 1
    volumes:
      # your existing traefik volumes...
      - traefik-signals:/signals:z
    networks:
      - traefik

  traefik-manager:
    image: ghcr.io/chr0nzz/traefik-manager:latest
    container_name: traefik-manager
    restart: always
    ports:
      - "5000:5000"
    environment:
      - COOKIE_SECURE=false
      - STATIC_CONFIG_PATH=/app/traefik.yml
      - RESTART_METHOD=poison-pill
      - SIGNAL_FILE_PATH=/signals/restart.sig
    volumes:
      - /path/to/traefik/dynamic.yml:/app/config/dynamic.yml:z
      - /path/to/traefik-manager/config:/app/config:z
      - /path/to/traefik-manager/backups:/app/backups:z
      - /path/to/traefik/traefik.yml:/app/traefik.yml:z
      - traefik-signals:/signals:z
    networks:
      - traefik

volumes:
  traefik-signals:
```

### Method 2: Direct socket

Enable the Podman API socket first - `systemctl --user enable --now podman.socket`, without `--user` for root - then mount it:

```yaml
services:
  traefik-manager:
    image: ghcr.io/chr0nzz/traefik-manager:latest
    container_name: traefik-manager
    restart: always
    ports:
      - "5000:5000"
    environment:
      - COOKIE_SECURE=false
      - STATIC_CONFIG_PATH=/app/traefik.yml
      - RESTART_METHOD=socket
      - TRAEFIK_CONTAINER=traefik
    volumes:
      - /path/to/traefik/dynamic.yml:/app/config/dynamic.yml:z
      - /path/to/traefik-manager/config:/app/config:z
      - /path/to/traefik-manager/backups:/app/backups:z
      - /path/to/traefik/traefik.yml:/app/traefik.yml:z
      # Root Podman:
      - /run/podman/podman.sock:/var/run/docker.sock:ro
      # Rootless Podman (replace 1000 with your UID):
      # - /run/user/1000/podman/podman.sock:/var/run/docker.sock:ro
```

### Environment variables

| Variable | Values | Default | Description |
|---|---|---|---|
| `STATIC_CONFIG_PATH` | path | - | Path to `traefik.yml` inside the container. Required for the Static Config and Plugins tabs. |
| `RESTART_METHOD` | `proxy`, `socket`, `poison-pill` | `proxy` | How to restart Traefik after a static config change. `proxy` and `socket` both restart the container over the socket. |
| `TRAEFIK_CONTAINER` | container name | `traefik` | Container to restart |
| `SIGNAL_FILE_PATH` | path | `/signals/restart.sig` | Signal file for the `poison-pill` method |

---

## Config file setup

### Single config file (default)

Mount one dynamic config file and point `CONFIG_PATH` at it:

```yaml
environment:
  - CONFIG_PATH=/app/config/dynamic.yml
volumes:
  - /path/to/traefik/dynamic.yml:/app/config/dynamic.yml:z
  - /path/to/traefik-manager/config:/app/config:z
  - /path/to/traefik-manager/backups:/app/backups:z
```

`/app/config/dynamic.yml` is the default, so mounting your file there needs no `CONFIG_PATH` at all.

### Multiple config files

Mount several Traefik dynamic configs and manage them from one UI. A **Config File** picker appears in the route, middleware and TLS option forms once more than one file is loaded.

:::tabs
== CONFIG_PATHS (explicit list)
Comma-separated list of config file paths inside the container. Use it to name exactly which files are managed.

```yaml
environment:
  # Single config file (default):
  # - CONFIG_PATH=/app/config/dynamic.yml
  # Multiple config files:
  - CONFIG_PATHS=/app/config/routes.yml,/app/config/services.yml
volumes:
  - /path/to/traefik-manager/config:/app/config:z
  - /path/to/traefik/routes.yml:/app/config/routes.yml:z
  - /path/to/traefik/services.yml:/app/config/services.yml:z
  - /path/to/traefik-manager/backups:/app/backups:z
```

== CONFIG_DIR (auto-discover from directory)
Point at a directory and every `.yml` and `.yaml` file inside it, subdirectories included, is picked up. Useful when the number of config files changes over time.

```yaml
environment:
  # Single config file (default):
  # - CONFIG_PATH=/app/config/dynamic.yml
  # Multiple config files (auto-discover):
  - CONFIG_DIR=/app/config/traefik
volumes:
  - /path/to/traefik-manager/config:/app/config:z
  - /path/to/traefik/config:/app/config/traefik:z
  - /path/to/traefik-manager/backups:/app/backups:z
```
:::

**Quadlet units:** set the variable in the `[Container]` section:

```ini
# Single config file (default):
# Environment=CONFIG_PATH=/app/config/dynamic.yml
# Multiple config files:
Environment=CONFIG_PATHS=/app/config/routes.yml,/app/config/services.yml
```

See the [Environment Variables](env-vars.md) reference for the full priority order.

---

## Behind Traefik (expose via subdomain)

Same as Docker. Remove `ports`, add labels, and put both containers on the same Podman network:

```yaml
services:
  traefik-manager:
    image: ghcr.io/chr0nzz/traefik-manager:latest
    container_name: traefik-manager
    restart: always
    environment:
      - COOKIE_SECURE=true
    volumes:
      - /path/to/traefik/dynamic.yml:/app/config/dynamic.yml:z
      - /path/to/traefik-manager/config:/app/config:z
      - /path/to/traefik-manager/backups:/app/backups:z
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik-manager.rule=Host(`manager.example.com`)"
      - "traefik.http.routers.traefik-manager.entrypoints=https"
      - "traefik.http.routers.traefik-manager.tls.certresolver=cloudflare"
      - "traefik.http.services.traefik-manager.loadbalancer.server.port=5000"
    networks:
      - traefik

networks:
  traefik:
    external: true
```

> `COOKIE_SECURE=true` is required when running behind HTTPS.


::: tip Real client IPs behind another proxy
With one proxy in front (Traefik), the default is correct. If something else sits in front of Traefik as well - Cloudflare, a load balancer, another reverse proxy - set `PROXY_FIX_HOPS` to the number of hops you control, so the login and audit log record the real client instead of the intermediate proxy:

```yaml
environment:
  - PROXY_FIX_HOPS=2
```

Only count hops you actually control: each trusted hop is one more `X-Forwarded-For` entry a client could forge. The [Client IP Diagnostic](tab-logs.md) in the nav bar shows what the app currently sees.
:::
