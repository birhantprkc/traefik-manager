# Mobile App

**traefik-manager-mobile** is a native Android companion app for managing Traefik Manager from your phone. Version 2.0 is a ground-up rewrite in Kotlin and Jetpack Compose.

::: info Using external auth (Authentik, Authelia, etc.)?
A `forwardAuth` middleware in front of Traefik Manager blocks the app before Traefik Manager ever sees the request, so no API key can help. See [external auth providers](#external-auth-providers) for the route split that fixes it.
:::

---

## Download

<MobileRelease />

<a href="https://play.google.com/store/apps/details?id=dev.chr0nzz.traefikmanager">
  <img src="https://github.com/chr0nzz/traefik-manager/raw/main/static/icons/GetItOnGooglePlay.svg" alt="Get it on Google Play" style="height:50px;width:auto" />
</a>

---

## Setup

### 1. Generate an API key

In the Traefik Manager web UI go to **Settings → Authentication → API Keys** and click **Add Key**. Enter a device name (e.g. `My Phone`) and click **Generate**. Copy the full key - it is only shown once.

::: tip One key per device
Each device should have its own key, up to 10 at once. Keys are identified by their device name in the settings list, so you can revoke a single device without affecting others.
:::

### 2. Configure the app

Open the mobile app and enter:

| Field | Value |
|---|---|
| Instance URL | Base URL of your Traefik Manager instance, e.g. `https://traefik-manager.example.com` |
| API Key | The key generated in step 1 |

Tap **Connect**.

### Do I need an API key?

The server decides whether a request must be authenticated at all:

| Built-in auth | OIDC | Authentication required |
|---|---|---|
| Off | Off | No - every request is accepted |
| Off | On | Yes |
| On | Either | Yes |

The app asks a narrower question - *does this server have any API keys* - and makes your entry match:

- **At least one key exists** - enter one, even if built-in auth is off. An empty field is rejected.
- **No keys exist** - leave the field empty. A key is rejected with *"API key auth is not enabled on this server"*, because there is nothing to check it against.

In practice: **if you have generated a key, use it.**

::: warning OIDC with no API keys
The one combination the app cannot resolve on its own. The server requires authentication, no keys exist, and the connect check itself needs authentication, so the app reports **"This server requires an API key"**. Generate one under **Settings → Authentication → API Keys**. OIDC covers the browser only.
:::

::: info Internal CAs and plain HTTP
Since v2.0.0 the Android app trusts CA certificates installed on the device, so instances secured by an internal/private CA work: install your root CA on the phone under **Settings → Security → Encryption & credentials → Install a certificate → CA certificate**, then connect with your `https://` URL. Plain `http://` URLs (LAN-only setups) are also supported.
:::

---

## Navigation

Navigation adapts to the screen. On a phone the bar sits at the bottom; on a tablet or an unfolded device it becomes a side rail. Everything else lives in a drawer, opened from the menu icon in the top bar.

The bar holds five destinations. By default those are **Dashboard**, **Routes**, **Middleware**, **Logs** and **CrowdSec**; pick your own five, and their order, under **Settings → Appearance and security → Choose items**. The same screen can hide the bar entirely, leaving the drawer as the way around.

### Drawer

The drawer holds every destination, grouped into four sections, plus the server switcher:

| Section | Destinations |
|---|---|
| Traffic | Dashboard, Routes, Middleware, Services, Route map |
| Observability | Logs, CrowdSec |
| Infrastructure | Certificates, Plugins |
| System | Backups, Settings |

::: tip Tabs follow the server
There is nothing to switch on in the app. Route map, Logs, CrowdSec, Certificates and Plugins each map to an optional tab in Traefik Manager, and appear as soon as that tab is enabled on the server you are connected to. Switch to an agent with a different set enabled and the destinations change with it.
:::

---

## Features

### Dashboard

The overview: router, service and middleware counts with their health, the providers in use, and your entry points. Below them your routes appear as an app launcher, grouped and tappable, sharing its configuration with the web Dashboard tab. A bell in the top bar carries unread notifications, and pull to refresh reloads.

### Routes

- Every HTTP, TCP and UDP route, with status, domain, target and attached middlewares
- Search, and filter by protocol or status
- Ping a route to check the backend is answering
- Tap a route for its detail pane; edit it, delete it, enable or disable it, or edit its raw YAML
- Disabling preserves the configuration - Traefik simply stops routing until you re-enable
- Add a route with the form, or drop to raw YAML for anything the form does not cover
- Multiple backends, sticky sessions, health checks and router priority
- Per-route certificate resolver, wildcard domains, and **Skip TLS verification** for self-signed backends

### Middleware

- Every middleware with its type, protocol and config
- Search, and filter by type
- **24 built-in wizards** covering Basic and Digest Auth, Forward Auth with Authentik, Authelia and Gatekeeper presets, OIDC Auth, IP Allow List, Rate Limit, In-Flight Requests, Secure Headers, CORS, redirects, prefix and path rewriting, Retry, Circuit Breaker, Buffering, Compress, Chain and Encoded Characters - the same set as the web app
- **Templates** - your saved YAML templates, managed from the middleware screen
- Raw YAML for anything the wizards do not cover

### Services

Every service Traefik knows about, with its backends, health and the routers using it. Search and filter by provider. Tap for the detail pane.

### Logs

The access log as analytics rather than a wall of text, mirroring the web app. Seven cards - status codes, response time, methods, domains, paths, clients and services - each with counts you can tap to filter the list. A **Where it fails** panel names the worst status-and-path pairs. Tap any entry for its full detail.

Domains need a JSON access log; on `common` format the card says so.

### CrowdSec

Built around the attack rather than the ban list, as the web app is. Cards for **attacking sources**, **networks**, **scenarios**, **targeted paths** (or accounts on an SSH host), **tooling** by user agent, and **bans in force**. Colour marks only what is not already handled, so a host being probed but absorbed cleanly reads calm.

- Search by address, scenario, network or path
- **Add decision** to ban an address, with type, duration and reason
- Remove a decision to unban
- Country flags and a ranked country strip when GeoIP is enabled; tap a country to filter

The screen states plainly when the LAPI is unreachable, or when only decisions or only alerts could be read, rather than showing zero as if it were fact.

### Certificates

Every certificate from your resolvers, with domains and expiry. Search, copy the domain list, and pull to refresh.

### Plugins

The plugins declared in your static config, with their module name and version. Search, copy a module name, and see which middlewares reference each plugin - or that none do. Read-only; install plugins from the web UI.

### Backups

Three tabs: **Dynamic**, **Static** and **Git**.

- Create a backup on demand, restore one, or delete it
- Restoring asks for confirmation first, and the server takes a backup of the current config before overwriting
- After restoring a static backup the screen tells you Traefik is still running the old config, and offers **Restart Traefik**
- The Git tab shows commit history with the changed files, pushes on demand, and restores from a commit

### Servers and agents

The server switcher sits at the top of the drawer, and the same list is under **Settings → Servers**. Switch between the host and any registered TMA agent, each with a live health indicator. Every screen then reflects that server's Traefik instance, and the destinations change to match its enabled tabs.

**Settings → Servers** also adds, renames and removes agents, and generates the compose snippet for a new one.

### Widgets

Two home screen widgets, from the same data as the app. Add one from your launcher's widget picker and its setup screen opens as you place it.

| Widget | Setup |
|---|---|
| Traefik Manager (small and large) | Which server, which card, and how often it refreshes. Stack up to four and tap to cycle. |
| App launcher | Your dashboard apps as a grid: which servers it lists, and whether names show. |

Both resize freely and re-flow to fit.

### Demo mode

**Try Demo** on the connect screen runs the app against built-in sample data, with no server required. Useful for looking around before you point it at anything real.

---

## Settings

**Settings** sits in the drawer under System, and opens a list of pages.

| Page | What is on it |
|---|---|
| Traefik connection | How this device reaches the server, plus domains, certificate resolvers and the direct Traefik API URL, with a **Test connection** button |
| Servers | The server list, and the compose snippet for a new agent (see [Servers and agents](#servers-and-agents)) |
| Authentication | Login status, and the API keys registered on the server |
| Notifications | Webhook delivery, a test send, and the notification history |
| Appearance and security | See below |
| Diagnostics | See below |
| About | Versions, and the open source licences |

### Appearance and security

| Setting | What it does |
|---|---|
| Theme | Light, Dark or System |
| Dynamic colour | Takes the palette from your wallpaper on Android 12+, while status colours stay semantically distinct |
| Hide the navigation bar | Frees the bottom of the screen; the drawer still reaches everything |
| Choose items | Which five screens sit in the bar, and their order |
| Dashboard layout | Rows or icons for the app launcher, shared with the web UI |
| Require unlock | Gates the app behind biometrics or your device PIN |

Everything here except the dashboard layout is stored on the device only.

### Diagnostics

What the server sees for your request: the trusted client IP that feeds the login rate limiter, audit log, `ipAllowList` and CrowdSec; the raw socket peer before any header is trusted; the trusted proxy hop count (`PROXY_FIX_HOPS`); the `X-Forwarded-For` chain and the forwarding headers as received. Each address is tagged public, private, CGNAT, loopback or link-local, so a private trusted IP alongside forwarding headers - the signature of a wrong `trustedIPs` or hop count - is visible at a glance.

---

## External auth providers

A `forwardAuth` middleware (Authentik, Authelia, Keycloak, etc.) intercepts **all** requests, including the mobile app's API calls, and redirects them to the provider's login page. The app cannot complete that OAuth/OIDC flow.

Split the Traefik route in two: one with `forwardAuth` for the web UI, and one without for `/api/*` that relies on Traefik Manager's own API key auth.

```yaml
http:
  routers:
    traefik-manager-web:
      rule: Host(`manager.example.com`) && !PathPrefix(`/api`)
      middlewares: [authentik]
      entryPoints: [websecure]
      service: traefik-manager
      tls:
        certResolver: cloudflare

    traefik-manager-api:
      rule: Host(`manager.example.com`) && PathPrefix(`/api`)
      entryPoints: [websecure]
      service: traefik-manager
      tls:
        certResolver: cloudflare

  services:
    traefik-manager:
      loadBalancer:
        servers:
          - url: http://traefik-manager:5000
```

::: warning Keep built-in auth enabled
With this split-route pattern, keep Traefik Manager's built-in auth **enabled** and generate API keys for your mobile devices. Without built-in auth, the `/api/*` route has no protection.
:::

---

## Requirements

| | |
|---|---|
| Traefik Manager (server) | **v1.10.1 or higher** |
| Android | 13+ (API 33) |

---

## Tech Stack

Version 2.x is native Android: Kotlin 2.4, Jetpack Compose with Material 3 Expressive, Hilt, Retrofit 3 with kotlinx.serialization, DataStore for storage, and Glance with WorkManager for the widgets. Release builds are minified and resource-shrunk with R8.

Version 1.x was built with Expo SDK 53 / React Native 0.79, and is still available on the `v1` branch.

::: tip Upgrading from 1.x
The rewrite ships under the same application id and is signed with the same certificate, so it installs straight over 1.x from either channel and keeps your server, API key and placed widgets. iOS is not supported in 2.x.
:::
