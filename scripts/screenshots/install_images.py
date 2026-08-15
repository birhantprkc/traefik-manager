import os

from PIL import Image

copied = 0
for theme in ("dark", "light"):
    for f in sorted(os.listdir(f"/new/{theme}")):
        im = Image.open(f"/new/{theme}/{f}").convert("RGB")
        im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
        im.save(f"/img/{theme}-{f[:-4]}.png", optimize=True)
        copied += 1

# Every screen, in the order a new user meets them: the feature tabs, then every
# settings pane, then the setup wizard. Provider tabs are left out - they repeat the
# routes view per provider and add nothing but length. The login page is left out too:
# a password box is not a feature. Agent API Keys is captured for the docs but kept out of
# the carousel: it is a drill-down inside Agents, and it shows an empty state here.
CAROUSEL = (
    "dashboard", "dashboard-icons", "dashboard-hover",
    "routes-cards", "routes-list", "routes-add-http", "routes-add-tcp", "routes-add-udp",
    "middlewares-cards", "middlewares-list", "middlewares-add",
    "services-cards", "services-list",
    "route-map", "tls-options", "certs",
    "logs", "crowdsec",
    "plugins", "plugins-add",
    "static-config",
    "settings-interface", "settings-auth-password", "settings-auth-apikeys",
    "settings-auth-oidc", "settings-backups", "settings-system", "settings-routes",
    "settings-connection", "settings-notifications", "settings-agents",
    "settings-about",
    "setup-welcome", "setup-connection", "setup-self-route", "setup-monitoring",
    "setup-crowdsec", "setup-git-backup", "setup-notifications", "setup-password",
)

for theme in ("dark", "light"):
    frames = []
    for n in CAROUSEL:
        p = f"/img/{theme}-{n}.png"
        if not os.path.exists(p):
            print(f"carousel: missing {theme}-{n}.png, skipped")
            continue
        frames.append(Image.open(p).convert("RGB").resize((1280, 720), Image.LANCZOS))
    frames[0].save(f"/img/readme-carousel-{theme}.gif", save_all=True,
                   append_images=frames[1:], duration=1600, loop=0, optimize=True)

print(f"{copied} screenshots installed, 2 carousel GIFs rebuilt from {len(CAROUSEL)} screens")
