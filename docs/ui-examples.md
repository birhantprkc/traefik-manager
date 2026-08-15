---
title: UI Examples
description: The Traefik Manager dashboard, routes, middlewares, services, logs, CrowdSec, settings and setup wizard, in light and dark.
---

# UI Examples

<style>
.shot-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 16px;
}
.shot-grid .screenshot { margin: 0; }
@media (max-width: 640px) {
  .shot-grid { grid-template-columns: repeat(2, 1fr); }
}</style>

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

## Setup Wizard

First run walks through everything in one pass: the Traefik connection, a route for the manager itself, which monitoring tabs to show, CrowdSec, git backup, notifications and the admin password.

<img class="screenshot dark-only" src="/images/dark-setup-welcome.png" alt="Setup wizard welcome">
<img class="screenshot light-only" src="/images/light-setup-welcome.png" alt="Setup wizard welcome">

<img class="screenshot dark-only" src="/images/dark-setup-connection.png" alt="Setup wizard Traefik connection">
<img class="screenshot light-only" src="/images/light-setup-connection.png" alt="Setup wizard Traefik connection">

<img class="screenshot dark-only" src="/images/dark-setup-self-route.png" alt="Setup wizard self route">
<img class="screenshot light-only" src="/images/light-setup-self-route.png" alt="Setup wizard self route">

<img class="screenshot dark-only" src="/images/dark-setup-monitoring.png" alt="Setup wizard monitoring tabs">
<img class="screenshot light-only" src="/images/light-setup-monitoring.png" alt="Setup wizard monitoring tabs">

<img class="screenshot dark-only" src="/images/dark-setup-crowdsec.png" alt="Setup wizard CrowdSec">
<img class="screenshot light-only" src="/images/light-setup-crowdsec.png" alt="Setup wizard CrowdSec">

<img class="screenshot dark-only" src="/images/dark-setup-git-backup.png" alt="Setup wizard git backup">
<img class="screenshot light-only" src="/images/light-setup-git-backup.png" alt="Setup wizard git backup">

<img class="screenshot dark-only" src="/images/dark-setup-notifications.png" alt="Setup wizard notifications">
<img class="screenshot light-only" src="/images/light-setup-notifications.png" alt="Setup wizard notifications">

<img class="screenshot dark-only" src="/images/dark-setup-password.png" alt="Setup wizard admin password">
<img class="screenshot light-only" src="/images/light-setup-password.png" alt="Setup wizard admin password">

## Android

The companion app, connected to the same instance. Every screen, in the theme you are reading this page in.

<div class="shot-grid">
  <img class="screenshot dark-only" src="/images/dark-mobile-overview.png" alt="Overview">
  <img class="screenshot light-only" src="/images/light-mobile-overview.png" alt="Overview">
  <img class="screenshot dark-only" src="/images/dark-mobile-routes.png" alt="Routes">
  <img class="screenshot light-only" src="/images/light-mobile-routes.png" alt="Routes">
  <img class="screenshot dark-only" src="/images/dark-mobile-route-detail.png" alt="Route detail">
  <img class="screenshot light-only" src="/images/light-mobile-route-detail.png" alt="Route detail">
  <img class="screenshot dark-only" src="/images/dark-mobile-route-add.png" alt="Add a route">
  <img class="screenshot light-only" src="/images/light-mobile-route-add.png" alt="Add a route">
  <img class="screenshot dark-only" src="/images/dark-mobile-route-edit.png" alt="Edit a route">
  <img class="screenshot light-only" src="/images/light-mobile-route-edit.png" alt="Edit a route">
  <img class="screenshot dark-only" src="/images/dark-mobile-middleware.png" alt="Middlewares">
  <img class="screenshot light-only" src="/images/light-mobile-middleware.png" alt="Middlewares">
  <img class="screenshot dark-only" src="/images/dark-mobile-middleware-detail.png" alt="Middleware detail">
  <img class="screenshot light-only" src="/images/light-mobile-middleware-detail.png" alt="Middleware detail">
  <img class="screenshot dark-only" src="/images/dark-mobile-middleware-add.png" alt="Add a middleware">
  <img class="screenshot light-only" src="/images/light-mobile-middleware-add.png" alt="Add a middleware">
  <img class="screenshot dark-only" src="/images/dark-mobile-middleware-edit.png" alt="Edit a middleware">
  <img class="screenshot light-only" src="/images/light-mobile-middleware-edit.png" alt="Edit a middleware">
  <img class="screenshot dark-only" src="/images/dark-mobile-services.png" alt="Services">
  <img class="screenshot light-only" src="/images/light-mobile-services.png" alt="Services">
  <img class="screenshot dark-only" src="/images/dark-mobile-service-detail.png" alt="Service detail">
  <img class="screenshot light-only" src="/images/light-mobile-service-detail.png" alt="Service detail">
  <img class="screenshot dark-only" src="/images/dark-mobile-logs.png" alt="Access logs">
  <img class="screenshot light-only" src="/images/light-mobile-logs.png" alt="Access logs">
  <img class="screenshot dark-only" src="/images/dark-mobile-log-detail.png" alt="Log entry detail">
  <img class="screenshot light-only" src="/images/light-mobile-log-detail.png" alt="Log entry detail">
  <img class="screenshot dark-only" src="/images/dark-mobile-crowdsec.png" alt="CrowdSec">
  <img class="screenshot light-only" src="/images/light-mobile-crowdsec.png" alt="CrowdSec">
  <img class="screenshot dark-only" src="/images/dark-mobile-crowdsec-add-decision.png" alt="Add a decision">
  <img class="screenshot light-only" src="/images/light-mobile-crowdsec-add-decision.png" alt="Add a decision">
  <img class="screenshot dark-only" src="/images/dark-mobile-certificates.png" alt="Certificates">
  <img class="screenshot light-only" src="/images/light-mobile-certificates.png" alt="Certificates">
  <img class="screenshot dark-only" src="/images/dark-mobile-plugins.png" alt="Plugins">
  <img class="screenshot light-only" src="/images/light-mobile-plugins.png" alt="Plugins">
  <img class="screenshot dark-only" src="/images/dark-mobile-plugin-detail.png" alt="Plugin detail">
  <img class="screenshot light-only" src="/images/light-mobile-plugin-detail.png" alt="Plugin detail">
  <img class="screenshot dark-only" src="/images/dark-mobile-backups-dynamic.png" alt="Dynamic config backups">
  <img class="screenshot light-only" src="/images/light-mobile-backups-dynamic.png" alt="Dynamic config backups">
  <img class="screenshot dark-only" src="/images/dark-mobile-backups-static.png" alt="Static config backups">
  <img class="screenshot light-only" src="/images/light-mobile-backups-static.png" alt="Static config backups">
  <img class="screenshot dark-only" src="/images/dark-mobile-backups-git.png" alt="Git backups">
  <img class="screenshot light-only" src="/images/light-mobile-backups-git.png" alt="Git backups">
  <img class="screenshot dark-only" src="/images/dark-mobile-drawer.png" alt="Navigation drawer">
  <img class="screenshot light-only" src="/images/light-mobile-drawer.png" alt="Navigation drawer">
  <img class="screenshot dark-only" src="/images/dark-mobile-settings.png" alt="Settings">
  <img class="screenshot light-only" src="/images/light-mobile-settings.png" alt="Settings">
</div>

## Tablet

The tablet layout swaps the bottom tab bar for a side rail and lays the cards out in two columns.

<div class="shot-grid">
  <img class="screenshot dark-only" src="/images/dark-tablet-overview.png" alt="Overview">
  <img class="screenshot light-only" src="/images/light-tablet-overview.png" alt="Overview">
  <img class="screenshot dark-only" src="/images/dark-tablet-routes.png" alt="Routes">
  <img class="screenshot light-only" src="/images/light-tablet-routes.png" alt="Routes">
  <img class="screenshot dark-only" src="/images/dark-tablet-route-detail.png" alt="Route detail">
  <img class="screenshot light-only" src="/images/light-tablet-route-detail.png" alt="Route detail">
  <img class="screenshot dark-only" src="/images/dark-tablet-route-add.png" alt="Add a route">
  <img class="screenshot light-only" src="/images/light-tablet-route-add.png" alt="Add a route">
  <img class="screenshot dark-only" src="/images/dark-tablet-route-edit.png" alt="Edit a route">
  <img class="screenshot light-only" src="/images/light-tablet-route-edit.png" alt="Edit a route">
  <img class="screenshot dark-only" src="/images/dark-tablet-middleware.png" alt="Middlewares">
  <img class="screenshot light-only" src="/images/light-tablet-middleware.png" alt="Middlewares">
  <img class="screenshot dark-only" src="/images/dark-tablet-middleware-detail.png" alt="Middleware detail">
  <img class="screenshot light-only" src="/images/light-tablet-middleware-detail.png" alt="Middleware detail">
  <img class="screenshot dark-only" src="/images/dark-tablet-middleware-add.png" alt="Add a middleware">
  <img class="screenshot light-only" src="/images/light-tablet-middleware-add.png" alt="Add a middleware">
  <img class="screenshot dark-only" src="/images/dark-tablet-middleware-edit.png" alt="Edit a middleware">
  <img class="screenshot light-only" src="/images/light-tablet-middleware-edit.png" alt="Edit a middleware">
  <img class="screenshot dark-only" src="/images/dark-tablet-services.png" alt="Services">
  <img class="screenshot light-only" src="/images/light-tablet-services.png" alt="Services">
  <img class="screenshot dark-only" src="/images/dark-tablet-service-detail.png" alt="Service detail">
  <img class="screenshot light-only" src="/images/light-tablet-service-detail.png" alt="Service detail">
  <img class="screenshot dark-only" src="/images/dark-tablet-logs.png" alt="Access logs">
  <img class="screenshot light-only" src="/images/light-tablet-logs.png" alt="Access logs">
  <img class="screenshot dark-only" src="/images/dark-tablet-log-detail.png" alt="Log entry detail">
  <img class="screenshot light-only" src="/images/light-tablet-log-detail.png" alt="Log entry detail">
  <img class="screenshot dark-only" src="/images/dark-tablet-crowdsec.png" alt="CrowdSec">
  <img class="screenshot light-only" src="/images/light-tablet-crowdsec.png" alt="CrowdSec">
  <img class="screenshot dark-only" src="/images/dark-tablet-crowdsec-add-decision.png" alt="Add a decision">
  <img class="screenshot light-only" src="/images/light-tablet-crowdsec-add-decision.png" alt="Add a decision">
  <img class="screenshot dark-only" src="/images/dark-tablet-certificates.png" alt="Certificates">
  <img class="screenshot light-only" src="/images/light-tablet-certificates.png" alt="Certificates">
  <img class="screenshot dark-only" src="/images/dark-tablet-plugins.png" alt="Plugins">
  <img class="screenshot light-only" src="/images/light-tablet-plugins.png" alt="Plugins">
  <img class="screenshot dark-only" src="/images/dark-tablet-plugin-detail.png" alt="Plugin detail">
  <img class="screenshot light-only" src="/images/light-tablet-plugin-detail.png" alt="Plugin detail">
  <img class="screenshot dark-only" src="/images/dark-tablet-backups-dynamic.png" alt="Dynamic config backups">
  <img class="screenshot light-only" src="/images/light-tablet-backups-dynamic.png" alt="Dynamic config backups">
  <img class="screenshot dark-only" src="/images/dark-tablet-backups-static.png" alt="Static config backups">
  <img class="screenshot light-only" src="/images/light-tablet-backups-static.png" alt="Static config backups">
  <img class="screenshot dark-only" src="/images/dark-tablet-backups-git.png" alt="Git backups">
  <img class="screenshot light-only" src="/images/light-tablet-backups-git.png" alt="Git backups">
  <img class="screenshot dark-only" src="/images/dark-tablet-drawer.png" alt="Navigation drawer">
  <img class="screenshot light-only" src="/images/light-tablet-drawer.png" alt="Navigation drawer">
  <img class="screenshot dark-only" src="/images/dark-tablet-settings.png" alt="Settings">
  <img class="screenshot light-only" src="/images/light-tablet-settings.png" alt="Settings">
</div>
