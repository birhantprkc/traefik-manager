# Beta

The `:beta` image tracks the `dev` branch, so it carries the next release before it ships. Running it means you see fixes early, and bugs get caught before they reach everyone else.

---

## Switch to beta

```yaml
image: ghcr.io/chr0nzz/traefik-manager:beta
```

```bash
docker compose pull traefik-manager && docker compose up -d traefik-manager
```

Or install fresh:

```bash
curl -fsSL https://get-traefik.xyzlab.dev/beta | bash
```

Agents have a `:beta` tag too. Keep the Host and its agents on the same channel.

---

## Roll back

```yaml
image: ghcr.io/chr0nzz/traefik-manager:latest
```

```bash
docker compose pull traefik-manager && docker compose up -d traefik-manager
```

Your `manager.yml` and backups are untouched by the switch, in either direction.

---

## Before you switch

`dev` is where fixes land the day they are written, so a beta image can be newer than any testing it has had. Treat it accordingly:

- Take a backup first, from **Settings - Backups**, or copy your config directory
- Expect the occasional rough edge. Anything that reaches `:latest` has been through a release
- A new setting written by a beta may not be understood by the older `:latest` build if you roll back

---

## Reporting

The useful bug report says what you did, what happened, and what you expected. Beyond that:

- **Logs from the moment it broke** - `docker compose logs traefik-manager` - are worth more than a description of the error
- **Your version**, from **Settings - About**
- **Your setup** where it is relevant: reverse proxy in front, agents, OIDC provider, CrowdSec

[Open an issue](https://github.com/chr0nzz/traefik-manager/issues/new/choose), or [start a discussion](https://github.com/chr0nzz/traefik-manager/discussions) if you are unsure whether something is a bug.

---

## Testing a specific fix

Issues are often fixed on `dev` and asked to be confirmed before release. When that happens you will be asked to pull `:beta` and try the exact thing that failed. That confirmation is the difference between a fix that is believed to work and one that is known to.

If you would rather not run beta permanently, switching over for one test and rolling back afterwards is a perfectly good way to help.

---

## What is in it

The [release notes](https://github.com/chr0nzz/traefik-manager/releases) cover each release. For what is on `dev` right now, the [commit history](https://github.com/chr0nzz/traefik-manager/commits/dev) is the source of truth.
