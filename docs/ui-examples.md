---
title: UI Examples
description: The Traefik Manager dashboard, routes, middlewares, services, logs, CrowdSec and settings, in light and dark.
---

# UI Examples

<style>
.shot-device { max-width: 360px; margin-left: auto; margin-right: auto; }
.shot-device-wide { max-width: 760px; margin-left: auto; margin-right: auto; }
</style>

**The screenshots below follow whichever theme you are reading this page in** - switch it with the toggle in the header to see the other one. Click any image to open it full screen.

## Dashboard

Every route as a launchable app, grouped into categories, with live health on each card and a second line only when something is wrong.

<img class="screenshot dark-only" src="/images/dark-dashboard.png" alt="Dashboard">
<img class="screenshot light-only" src="/images/light-dashboard.png" alt="Dashboard">

Switch the categories to an icon grid under Settings -> Interface, and the dashboard becomes an app launcher.

<img class="screenshot dark-only" src="/images/dark-dashboard-icons.png" alt="Dashboard icon grid">
<img class="screenshot light-only" src="/images/light-dashboard-icons.png" alt="Dashboard icon grid">

## Routes

Card and list views over every router Traefik knows about, from every provider, with the stat panel and entry points above.

<img class="screenshot dark-only" src="/images/dark-routes-cards.png" alt="Routes card view">
<img class="screenshot light-only" src="/images/light-routes-cards.png" alt="Routes card view">

<img class="screenshot dark-only" src="/images/dark-routes-list.png" alt="Routes list view">
<img class="screenshot light-only" src="/images/light-routes-list.png" alt="Routes list view">

Adding a route is a slide-in form. HTTP routes get domains, backends, load balancing, entry points and middlewares; TCP and UDP get what applies to them and nothing else.

<img class="screenshot dark-only" src="/images/dark-routes-add-http.png" alt="Add HTTP route">
<img class="screenshot light-only" src="/images/light-routes-add-http.png" alt="Add HTTP route">

<img class="screenshot dark-only" src="/images/dark-routes-add-tcp.png" alt="Add TCP route">
<img class="screenshot light-only" src="/images/light-routes-add-tcp.png" alt="Add TCP route">

<img class="screenshot dark-only" src="/images/dark-routes-add-udp.png" alt="Add UDP route">
<img class="screenshot light-only" src="/images/light-routes-add-udp.png" alt="Add UDP route">

## Middlewares

The same card and list treatment for middlewares, with usage counts, and a form that knows the config shape of every middleware type.

<img class="screenshot dark-only" src="/images/dark-middlewares-cards.png" alt="Middlewares card view">
<img class="screenshot light-only" src="/images/light-middlewares-cards.png" alt="Middlewares card view">

<img class="screenshot dark-only" src="/images/dark-middlewares-list.png" alt="Middlewares list view">
<img class="screenshot light-only" src="/images/light-middlewares-list.png" alt="Middlewares list view">

<img class="screenshot dark-only" src="/images/dark-middlewares-add.png" alt="Add middleware">
<img class="screenshot light-only" src="/images/light-middlewares-add.png" alt="Add middleware">

## Services

Every service with its backends, health and the routers using it.

<img class="screenshot dark-only" src="/images/dark-services-cards.png" alt="Services card view">
<img class="screenshot light-only" src="/images/light-services-cards.png" alt="Services card view">

<img class="screenshot dark-only" src="/images/dark-services-list.png" alt="Services list view">
<img class="screenshot light-only" src="/images/light-services-list.png" alt="Services list view">

## Route Map

The full path of a request, entry point to backend, as a live diagram.

<img class="screenshot dark-only" src="/images/dark-route-map.png" alt="Route map">
<img class="screenshot light-only" src="/images/light-route-map.png" alt="Route map">

## Static Config

`traefik.yml` as editable cards: entry points, certificate resolvers, providers, logging, observability and system, with raw YAML one click away.

<img class="screenshot dark-only" src="/images/dark-static-config.png" alt="Static config tab">
<img class="screenshot light-only" src="/images/light-static-config.png" alt="Static config tab">

## TLS Options

TLS profiles with minimum versions, cipher suites and mTLS, assignable per route.

<img class="screenshot dark-only" src="/images/dark-tls-options.png" alt="TLS options">
<img class="screenshot light-only" src="/images/light-tls-options.png" alt="TLS options">

## Certificates

Every certificate from every resolver, with expiry warnings.

<img class="screenshot dark-only" src="/images/dark-certs.png" alt="Certificates">
<img class="screenshot light-only" src="/images/light-certs.png" alt="Certificates">

## Logs

The access log as clickable analytics: status codes, response times, methods, domains, paths, clients and services, where every count is a filter.

<img class="screenshot dark-only" src="/images/dark-logs.png" alt="Access logs">
<img class="screenshot light-only" src="/images/light-logs.png" alt="Access logs">

## CrowdSec

The attack surface: who is probing, from which networks and countries, with what tooling, and whether CrowdSec absorbed it.

<img class="screenshot dark-only" src="/images/dark-crowdsec.png" alt="CrowdSec">
<img class="screenshot light-only" src="/images/light-crowdsec.png" alt="CrowdSec">

## Plugins

Installed Traefik plugins, and a guided install straight from the catalog.

<img class="screenshot dark-only" src="/images/dark-plugins.png" alt="Plugins">
<img class="screenshot light-only" src="/images/light-plugins.png" alt="Plugins">

<img class="screenshot dark-only" src="/images/dark-plugins-add.png" alt="Install a plugin">
<img class="screenshot light-only" src="/images/light-plugins-add.png" alt="Install a plugin">

## Settings

Interface, authentication with API keys and OIDC, backups, system and route monitoring, and the connection to Traefik itself.

<img class="screenshot dark-only" src="/images/dark-settings-interface.png" alt="Interface settings">
<img class="screenshot light-only" src="/images/light-settings-interface.png" alt="Interface settings">

<img class="screenshot dark-only" src="/images/dark-settings-auth-password.png" alt="Authentication settings">
<img class="screenshot light-only" src="/images/light-settings-auth-password.png" alt="Authentication settings">

<img class="screenshot dark-only" src="/images/dark-settings-auth-apikeys.png" alt="API keys">
<img class="screenshot light-only" src="/images/light-settings-auth-apikeys.png" alt="API keys">

<img class="screenshot dark-only" src="/images/dark-settings-auth-oidc.png" alt="OIDC and SSO">
<img class="screenshot light-only" src="/images/light-settings-auth-oidc.png" alt="OIDC and SSO">

<img class="screenshot dark-only" src="/images/dark-settings-backups.png" alt="Backups">
<img class="screenshot light-only" src="/images/light-settings-backups.png" alt="Backups">

<img class="screenshot dark-only" src="/images/dark-settings-system.png" alt="System monitoring">
<img class="screenshot light-only" src="/images/light-settings-system.png" alt="System monitoring">

<img class="screenshot dark-only" src="/images/dark-settings-routes.png" alt="Route monitoring">
<img class="screenshot light-only" src="/images/light-settings-routes.png" alt="Route monitoring">

<img class="screenshot dark-only" src="/images/dark-settings-connection.png" alt="Connection settings">
<img class="screenshot light-only" src="/images/light-settings-connection.png" alt="Connection settings">

<img class="screenshot dark-only" src="/images/dark-settings-about.png" alt="About">
<img class="screenshot light-only" src="/images/light-settings-about.png" alt="About">

## Android and tablet

The companion app, connected to the same instance. Both tours cycle through every screen - overview, routes, middlewares, services, logs, CrowdSec, certificates, plugins, backups and settings.

### Phone

<img class="screenshot shot-device dark-only" src="/images/mobile-dark.gif" alt="Traefik Manager on a phone">
<img class="screenshot shot-device light-only" src="/images/mobile-light.gif" alt="Traefik Manager on a phone">

### Tablet

The tablet layout swaps the bottom tab bar for a side rail and lays the cards out in two columns.

<img class="screenshot shot-device-wide dark-only" src="/images/tablet-dark.gif" alt="Traefik Manager on a tablet">
<img class="screenshot shot-device-wide light-only" src="/images/tablet-light.gif" alt="Traefik Manager on a tablet">
