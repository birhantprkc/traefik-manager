# Reset Password

This page covers all methods for recovering access to Traefik Manager.

---

## Method 1 - CLI reset (recommended)

This is the fastest method when you can exec into the container.

:::tabs
== Docker
```bash
docker exec traefik-manager flask reset-password
```

== Podman
```bash
podman exec traefik-manager flask reset-password
```

== Unraid
Open the Unraid dashboard → Docker tab → click the Traefik Manager icon → **Console**, then run:
```bash
flask reset-password
```

== Linux (native)
```bash
cd /opt/traefik-manager
SETTINGS_PATH=/var/lib/traefik-manager/manager.yml \
  venv/bin/flask reset-password
```
:::

A new temporary password is printed to the terminal. On your next login you are sent to a forced password-change screen before you reach the dashboard.

::: info Lost your authenticator too?
Two-factor authentication is **preserved** by default. Add `--disable-otp` to the same command to reset the password and turn 2FA off in one step, then re-enable it from **Settings → Authentication → Password & 2FA**.
:::

::: warning
The reset also sets `setup_password_reset: true` in `manager.yml`, which leaves the `/setup` page open to anyone who can reach Traefik Manager. Only setting a password on that page clears the flag - the forced-change screen does not. So either set your new password at `https://your-traefik-manager.example.com/setup`, or remove the key from `manager.yml` afterwards and restart.
:::

---

## Method 2 - Manual reset via manager.yml

Use this if you cannot exec into the container (e.g. the container won't start).

**1. Open `manager.yml`** in your config volume:

```bash
nano /path/to/traefik-manager/config/manager.yml
```

**2. Add the reset flag:**

```yaml
setup_password_reset: true
```

**3. Restart:**

```bash
docker compose restart traefik-manager
```

**4. Open `/setup`** (`https://your-traefik-manager.example.com/setup`). You are asked for a new password and nothing else. Setting it clears the flag and signs you in.

::: warning
While the flag is set, anyone who can reach Traefik Manager can set the password. Restart, set the new password, and confirm you are signed in.
:::

## Method 3 - Pre-set a known password

To set a specific password instead of the auto-generated one, generate a bcrypt hash and write it directly to `manager.yml`:

```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'yournewpassword', bcrypt.gensalt()).decode())"
```

Update `manager.yml`:

```yaml
password_hash: "$2b$12$..."
must_change_password: false
setup_complete: true
```

Restart the container - no wizard, no forced change, log in immediately with the password you set.

See [manager.yml reference](manager-yml.md) for all available fields.

---

## Two-factor authentication

### Enable 2FA

1. **Settings → Authentication → Password & 2FA → Enable 2FA**
2. Scan the QR code with your TOTP app (Google Authenticator, Authy, 1Password, etc.)
3. Enter the 6-digit code to confirm - 2FA is now active

### Disable 2FA (while logged in)

**Settings → Authentication → Password & 2FA → Disable 2FA**. No code is required - you are already authenticated.

### Disable 2FA (locked out)

Use the `--disable-otp` flag with the CLI reset command shown above.
