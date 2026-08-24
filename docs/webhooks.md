# Notifications

Traefik Manager can push every notification event to as many destinations as you like. Each destination is a **channel** with its own type, credentials, filters and schedule.

Configure them in **Settings - Notifications**.

Every message the UI shows as a toast is also kept in the notification drawer behind the bell, so a message that disappears before you read it can still be found. Messages raised in the browser (validation errors, failed requests) are recorded there but are not sent to channels. The exceptions are the **Ping all** summary and version-update notices, which are raised by the UI and do fire a channel. Repeats of the same message within 8 seconds are recorded once.

::: tip Upgrading
The single webhook from earlier versions is migrated on first start into a channel named **Webhook**, keeping its type, URL and credentials. Nothing to do.
:::

---

## Add a channel

1. Open **Settings - Notifications** and click **Add channel**.
2. Pick the **Type** and give the channel a **Name**.
3. Fill in the credentials for that type (see below).
4. Choose its **Categories**, **Minimum severity** and **Schedule**.
5. Click **Test** to send a test message immediately.
6. Settings save automatically on blur.

Channels are independent. A phone channel can take errors only, while a Discord channel takes everything.

The setup wizard creates the first channel for you: pick a type, fill in its fields, and the channel is saved with every category, minimum severity **Info** and immediate delivery. Leave the fields blank to skip the step.

---

## Types

| Type         | Needs                                                                   |
| --------------| -------------------------------------------------------------------------|
| Discord      | Webhook URL                                                             |
| Slack        | Incoming webhook URL                                                    |
| ntfy         | Topic URL, optional username and password                               |
| Generic JSON | Endpoint URL, optional username and password                            |
| Gotify       | Server URL, app token                                                   |
| Pushover     | App token, user key                                                     |
| Pushbullet   | Access token                                                            |
| Telegram     | Bot token, chat ID                                                      |
| Mobile app   | Registered by the Traefik Manager Android app. Do not create it by hand |

### Discord

Paste your Discord webhook URL (`https://discord.com/api/webhooks/...`).

```json
{
  "embeds": [{
    "title": "Route my-app updated",
    "color": 4176208,
    "footer": { "text": "Traefik Manager - 2026-05-18 12:00:00" }
  }]
}
```

Color changes by severity: green for success, yellow for warnings, red for errors, blue for info.

---

### Slack

Paste an incoming webhook URL (`https://hooks.slack.com/...`).

```json
{ "text": ":white_check_mark: *Traefik Manager* - Route my-app updated" }
```

---

### ntfy.sh / self-hosted ntfy

Paste your topic URL - either the hosted service or a self-hosted instance.

```
https://ntfy.sh/your-topic
https://ntfy.yourdomain.com/your-topic
```

If your ntfy instance requires authentication, fill in **Username** and **Password**.

The message is sent as the plain-text body, with these headers:

| Header | Value |
|---|---|
| `X-Title` | `Traefik Manager` |
| `X-Priority` | `4` for warnings/errors, `3` for info/success |
| `X-Tags` | `warning`, `rotating_light`, `white_check_mark`, or `information_source` |

---

### Generic JSON

Sends a plain JSON body to any HTTP endpoint. Optionally set **Username** and **Password** for basic auth.

```json
{
  "event": "success",
  "message": "Route my-app updated",
  "timestamp": "2026-05-18 12:00:00"
}
```

`event` is the severity, not the specific action - see the table below.

---

### Gotify

| Field | Value |
|---|---|
| Server URL | Your Gotify base URL, e.g. `https://gotify.example.com` |
| App token | Created per application in Gotify |

In Gotify: **Apps - Create Application**, then copy that application's token. Client tokens do not work for sending.

---

### Pushover

| Field | Value |
|---|---|
| App token | From **Create an Application/API Token** at [pushover.net/apps/build](https://pushover.net/apps/build) |
| User key | Shown on your [pushover.net](https://pushover.net) dashboard |

Pushover allows 10,000 messages per month per application, free. A busy instance on `immediate` can reach that - use a digest or trim the categories.

---

### Pushbullet

| Field | Value |
|---|---|
| Access token | **Settings - Account - Create Access Token** at [pushbullet.com](https://www.pushbullet.com/#settings/account) |

Pushes go to every device signed in to that account.

---

### Telegram

| Field | Value |
|---|---|
| Bot token | From [@BotFather](https://t.me/BotFather): send `/newbot`, follow the prompts, copy the token |
| Chat ID | See below |

Finding the chat ID:

1. Open a chat with your new bot and send it any message. A bot cannot message you first.
2. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser, `<TOKEN>` replaced with your bot token.
3. Read `result[0].message.chat.id`. That number is your chat ID. Personal chats are positive, groups are negative and start with `-100`.

If `getUpdates` returns `{"ok":true,"result":[]}`, the bot has no messages yet - send it one and reload.

For a group: add the bot to the group, send a message there, then read the negative `chat.id` from the same URL.

---

## Control

Three layers decide whether a channel hears an event, in this order.

| Layer | Question |
|---|---|
| Categories | Is this kind of event one this channel cares about? |
| Minimum severity | Is it important enough? |
| Schedule | Send it now, hold it for a digest, or hold it until quiet hours end? |

### Categories

| Category | Contents |
|---|---|
| `config` | Routes, middlewares, services and static config saved, deleted, enabled or disabled |
| `backup` | Backups created, restored or deleted, and git pushes and restores |
| `security` | Logins, failed logins, password and 2FA changes, API key changes |
| `traefik` | Traefik restarts, reachability changes and config reload failures |
| `certs` | Certificate issue, renewal and expiry warnings |
| `crowdsec` | Local CrowdSec decisions, aggregated per window |
| `agent` | Remote agents connecting, dropping, registering or failing to authenticate |
| `update` | New Traefik Manager and Traefik versions |

A channel with no categories selected hears all of them.

### Minimum severity

`info` - `success` - `warning` - `error`, lowest to highest. A channel set to `warning` hears warnings and errors only.

### Schedule

| Setting | Effect |
|---|---|
| Immediate | Send each message as it happens |
| Hourly | One combined report per hour |
| Daily | One combined report per day |
| Quiet hours | Hold everything raised inside the window, e.g. `22:00-07:00` |
| Break through | Send `error` messages even during quiet hours |

Quiet hours use the container's timezone. Set `TZ` if that is not yours.

---

## Quiet hours

Messages raised during the window are **queued, not dropped**. When the window ends the channel gets **one** report that collapses everything held, grouped by category. It is a summary, not a replay.

```
Traefik Manager - held during quiet hours 22:00-07:00

config    6 events - 4 routes saved, 1 route deleted, 1 static config saved
certs     2 events - renewed app.example.com, wiki.example.com
crowdsec  1 event  - 14 local decisions
backup    1 event  - nightly backup created
```

Hourly and daily digests collapse the same way. Nothing held means nothing sent.

---

## CrowdSec is aggregated

CrowdSec events report per window, not per ban. A typical instance carries tens of thousands of community blocklist decisions and only a handful earned on your own machine, so one message per decision is unusable.

One window becomes one message, naming the source, its country and network, and every scenario it tripped:

```
KWA: 80.94.95.211 (🇩🇪, AS24940 Hetzner) tripped 5 scenarios, 21 events in
the last 10 minutes: http-bad-user-agent, http-crawl-non-statics,
http-probing, http-sensitive-files and 1 more
```

Country and network come from the `crowdsecurity/geoip-enrich` parser on the machine that raised the alert. Without it the address is still named, just without the detail. A client with no flag font shows the two letter code instead.

---

## Background checks

These run inside the container on their own schedule, so an instance nobody has open still reports. One worker runs them, never all of them.

| Check | Every | Servers | Raises |
|---|---|---|---|
| Certificates | daily | Host and agents | expiry at 14 days, 3 days and on the day |
| Traefik | 1 min | Host and agents | reachability changes |
| Agents | 2 min | agents | agent unreachable, agent back online |
| GeoIP | daily | Host | database refreshed or too old to refresh |
| CrowdSec | 5 min | Host and agents | one aggregated message per window |
| Updates | daily | Host | a new Traefik Manager or Traefik release, once per version |

Each fires once per change, not once per cycle.

Messages from an agent are prefixed with its name, so `VPS One: Traefik API is unreachable`
tells you which server without opening the app. Host messages carry no prefix.

An agent that is unreachable reports once. Its certificate, Traefik and CrowdSec checks are
skipped for that cycle rather than each reporting the same outage separately.

---

## Storage

Channels live in `manager.yml` under `notification_channels`, with every credential encrypted at rest. See [`notification_channels`](./manager-yml#notification-channels).

The notification log lives in `notifications.yml` in the config directory and keeps the 200 newest entries. An empty `notifications.yml.lock` sits beside it and can be ignored.

---

## Storage

The notification log lives in `notifications.yml` in the config directory and keeps the 200 newest entries. An empty `notifications.yml.lock` sits beside it and can be ignored.

---

## Event types

| Type | When |
|---|---|
| `success` | Route or middleware saved, TLS profile saved, static config saved, backup created, plugin installed, git push succeeded |
| `warning` | Route or middleware deleted, backup restored or deleted, git restore, Traefik restarted, ping failures |
| `error` | Git push, backup or restore failures |
| `info` | Login events, ping all results, version updates |
