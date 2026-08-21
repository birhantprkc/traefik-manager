# Notification Webhooks

Traefik Manager can fire an HTTP POST to a webhook URL on every notification event - route saved, route deleted, backup restored, ping results, and more.

Configure webhooks in **Settings - Notifications**.

Every message the UI shows as a toast is also kept in the notification drawer behind the bell, so a message that disappears before you read it can still be found. Messages raised in the browser (validation errors, failed requests) are recorded there but are not sent to webhooks. The exceptions are the **Ping all** summary and version-update notices, which are raised by the UI and do fire a webhook. Repeats of the same message within 8 seconds are recorded once.

---

## Setup

1. Open **Settings** and go to the **Notifications** panel.
2. Select the **Type** that matches your destination.
3. Paste the **Webhook URL**.
4. For ntfy or generic endpoints that require authentication, fill in **Username** and **Password** (leave blank if not needed).
5. Click **Test** to send a test payload immediately.
6. Settings save automatically on blur.

---

## Supported types

### Discord

Select **Discord** and paste your Discord webhook URL (`https://discord.com/api/webhooks/...`).

Payload format:
```json
{
  "embeds": [{
    "title": "Route my-app updated",
    "color": 4176208,
    "footer": { "text": "Traefik Manager - 2026-05-18 12:00:00" }
  }]
}
```

Color changes by event type: green for success, yellow for warnings, red for errors, blue for info.

---

### Slack

Select **Slack** and paste an incoming webhook URL (`https://hooks.slack.com/...`).

Payload format:
```json
{ "text": ":white_check_mark: *Traefik Manager* - Route my-app updated" }
```

---

### ntfy.sh / self-hosted ntfy

Select **ntfy** and paste your topic URL - either the hosted service or a self-hosted instance.

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

Payload format:
```json
{
  "event": "success",
  "message": "Route my-app updated",
  "timestamp": "2026-05-18 12:00:00"
}
```

`event` is the event type, not the specific action - see the table below.

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
