# Agent API Reference

The Traefik Manager Agent (TMA) exposes an HTTP API on port 8090. Every endpoint except `/health` requires authentication.

## Authentication

Send your API key in the `X-Api-Key` header:

```http
X-Api-Key: your-api-key-here
```

`Authorization: Bearer <key>` works too.

The key is trimmed of surrounding whitespace on both sides - in the header and in `TMA_API_KEY` - so a trailing newline from a secrets file or a copy-paste does not cause a `401`.

TM handles authentication automatically when proxying calls through `/api/agents/proxy/<id>/...`.

## Rate limiting

`/api/` requests are rate-limited per IP using `TMA_RATE_LIMIT` (default: 300 requests/minute), and return `429 Too Many Requests` when exceeded. Set `TMA_RATE_LIMIT=0` to disable. The default is generous because TM makes many API calls per tab switch; lower it only if you need stricter access control.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check - no auth required |
| GET | `/api/traefik/overview` | Traefik API overview |
| GET | `/api/traefik/routers` | Routers across all protocols - returns `{"http":[...],"tcp":[...],"udp":[...]}` |
| GET | `/api/traefik/services` | Services across all protocols - returns `{"http":[...],"tcp":[...],"udp":[...]}` |
| GET | `/api/traefik/middlewares` | Middlewares across all protocols - returns `{"http":[...],"tcp":[...]}` |
| GET | `/api/traefik/entrypoints` | Entrypoints |
| GET | `/api/traefik/version` | Traefik version |
| GET | `/api/traefik/logs` | Last N access log lines (requires `ACCESS_LOG_PATH`) - `?lines=100`, capped at 1000 |
| GET | `/api/traefik/certs` | Certificates from acme.json (requires `ACME_JSON_PATH`) |
| GET | `/api/traefik/plugins` | Plugins declared in the agent's static config (requires `STATIC_CONFIG_PATH`) |
| GET | `/api/configs` | Read dynamic config file(s) |
| POST | `/api/configs` | Write a dynamic config file (creates a `.bak` before writing) - body: `{"name": "...", "content": "<yaml>"}` |
| GET | `/api/static` | Read static config (requires `STATIC_CONFIG_PATH`) |
| POST | `/api/static` | Write static config - body: `{"content": "<yaml>"}` |
| GET | `/api/static/status` | Restart method info |
| POST | `/api/static/restart` | Restart Traefik (requires `RESTART_METHOD`) |
| GET | `/api/crowdsec/decisions` | CrowdSec active decisions (requires CrowdSec config) |
| POST | `/api/crowdsec/decisions` | Add a decision - body: `{"value": "<ip>", "type": "ban", "duration": "24h", "reason": "..."}`; `type` is `ban`, `captcha` or `bypass` |
| GET | `/api/crowdsec/alerts` | CrowdSec recent alerts - `?limit=N` (0 to 100000, defaults to `CROWDSEC_ALERT_LIMIT`). Returns `X-CS-Alert-Limit` and `X-CS-Alert-Capped` (`1` when the response hit the limit) |
| DELETE | `/api/crowdsec/decisions/<id>` | Unban an IP |
| GET | `/api/backups` | List local `.bak` backup files |
| POST | `/api/backup/create` | Create `.bak` backups for all config files (one per file) |
| POST | `/api/restore/<filename>` | Restore a config file from a `.bak` backup |
| POST | `/api/backup/delete/<filename>` | Delete a `.bak` backup file |
| GET | `/api/backup/git/status` | Git backup status |
| POST | `/api/backup/git/push` | Manual git push |
| POST | `/api/backup/git/test` | Test git connectivity |
| GET | `/api/backup/git/commits` | Last 50 commits |
| GET | `/api/backup/git/commit/<sha>/diff` | Per-file diff for a commit |
| POST | `/api/backup/git/restore/<sha>` | Restore configs from a git commit |
| DELETE | `/api/backup/git/repo` | Reset (delete) local git repo clone |
| GET | `/api/routes/<id>/raw` | Raw YAML for a single route (router + service block) - `id` is the route name or `configFile::routeName` |
| POST | `/api/routes/<id>/raw` | Save raw YAML for a route - body: `{"content": "<yaml>"}` |
| GET | `/api/keys` | List API keys |
| POST | `/api/keys` | Create an API key - body: `{"name": "..."}` |
| DELETE | `/api/keys/<id>` | Delete an API key |

## Health check

```http
GET /health
```

Response (no auth required):
```json
{"ok": true, "version": "1.11.0"}
```

## Error responses

| Status | Meaning |
|---|---|
| 400 | Bad request (invalid body or filename, `RESTART_METHOD` not configured) |
| 401 | Missing or invalid API key |
| 404 | Endpoint not available (e.g. `STATIC_CONFIG_PATH` not set) |
| 429 | Rate limit exceeded |
| 500 | Internal error |
| 502 | Cannot reach Traefik or the CrowdSec LAPI |

All errors return `{"error": "message", "ok": false}`.

## Backup format

Local backups are per-file `.bak` files, not zip archives, named `filename.YYYYMMDD_HHMMSS.bak` (e.g. `dynamic.yml.20250601_143022.bak`) with a UTC timestamp. When restoring, the agent strips the timestamp suffix to recover the original filename and writes it back to `CONFIG_PATH` - or to `STATIC_CONFIG_PATH` when the recovered name is that of the static config file. A `.bak` of the destination is taken before the restore overwrites it.

`POST /api/backup/create` creates one `.bak` per config file found in `CONFIG_PATH` (and `STATIC_CONFIG_PATH` if configured) in a single request. `POST /api/configs` also creates a `.bak` for the affected file before writing.

## Traefik data envelope

`/api/traefik/routers`, `/api/traefik/services` and `/api/traefik/middlewares` do NOT proxy the Traefik API directly. They fetch every protocol, following the API's pagination, and return a structured envelope:

- `/api/traefik/routers` - `{"http": [...], "tcp": [...], "udp": [...]}`
- `/api/traefik/services` - `{"http": [...], "tcp": [...], "udp": [...]}`
- `/api/traefik/middlewares` - `{"http": [...], "tcp": [...]}`

This matches the format TM expects for its own Traefik API calls, so agent data renders identically to local data.

If the agent cannot reach its Traefik API, or Traefik answers with a non-`200` status, these endpoints return `502` with `{"error": "traefik unavailable...", "ok": false}`. Earlier versions turned a non-`200` response into an empty list with status `200`, so a broken Traefik looked the same as one with nothing configured.

## API keys

The agent supports multiple named API keys, stored in `<BACKUP_DIR>/api_keys.json`. Only a SHA-256 hash of each key is stored - the raw key is shown once at creation and cannot be recovered. The primary `TMA_API_KEY` from the environment always works regardless of the key store. Create, list and delete additional keys via `/api/keys`, which is useful when several TM instances connect to the same agent.

## Proxying through TM

TM proxies agent calls server-side via `/api/agents/proxy/<agent-id>/<path>`. For example:

```
GET /api/agents/proxy/abc123/traefik/routers
```

Routes to:
```
GET https://agent-host:8090/api/traefik/routers
```

TM injects the `X-Api-Key` header automatically using the stored (encrypted) key, and passes the agent's `X-*` response headers back to the caller, except `x-api-key`, `x-csrf-token`, `x-frame-options` and `x-powered-by`.
