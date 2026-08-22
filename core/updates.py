"""Release checks for Traefik Manager and Traefik, run by the notification monitor.

The browser used to ask GitHub on every page load, so an instance nobody had
open never learned about a release. These run on the monitor schedule instead
and announce each version once.
"""
import requests

from core import env
from core import monitor as monitor_mod
from core import traefik as traefik_mod
from core.env import logger

UPDATE_INTERVAL = 86400
UPDATE_TIMEOUT  = 10
TRAEFIK_REPO    = 'traefik/traefik'
GITHUB_LATEST   = 'https://api.github.com/repos/{repo}/releases/latest'


def _strip_v(value) -> str:
    text = str(value or '').strip()
    return text[1:] if text[:1] in ('v', 'V') else text


def _version_parts(value) -> list:
    parts = []
    for chunk in _strip_v(value).split('.'):
        digits = ''
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)
    return parts


def compare_versions(a, b) -> int:
    """Positive when a is newer than b, the browser compareVersions in Python."""
    pa, pb = _version_parts(a), _version_parts(b)
    for i in range(max(len(pa), len(pb))):
        diff = (pa[i] if i < len(pa) else 0) - (pb[i] if i < len(pb) else 0)
        if diff != 0:
            return diff
    return 0


def latest_release(repo: str) -> str:
    """Tag of the newest published release, without the leading v."""
    try:
        resp = requests.get(GITHUB_LATEST.format(repo=repo), timeout=UPDATE_TIMEOUT,
                            headers={'Accept': 'application/vnd.github.v3+json'})
        if resp.status_code != 200:
            logger.debug(f"Update check for {repo} returned HTTP {resp.status_code}")
            return ''
        data = resp.json()
    except Exception as e:
        logger.debug(f"Update check for {repo} failed: {e}")
        return ''
    return _strip_v((data or {}).get('tag_name')) if isinstance(data, dict) else ''


def running_traefik_version() -> str:
    """Version Traefik reports on /api/version, empty when it cannot be reached."""
    info = traefik_mod.traefik_api_get('/api/version')
    return _strip_v(info.get('Version')) if isinstance(info, dict) else ''


def _update_alert(key, product, current, latest, seen):
    if not latest or seen.get(key) == latest:
        return None
    if compare_versions(latest, current) <= 0:
        return None
    seen[key] = latest
    return ('info', f"{product} v{latest} is available - update now", 'update')


def check_updates(seen: dict = None) -> list:
    """Announce a newer Traefik Manager or Traefik release once per version.

    seen holds the versions already announced and defaults to the monitor's own
    persisted state, so a release is not repeated on the next run.
    """
    if seen is None:
        seen = monitor_mod._section('updates')
    raised = []
    for key, product, repo, current in (
            ('manager', 'Traefik Manager', env.GITHUB_REPO,   env.APP_VERSION),
            ('traefik', 'Traefik',         TRAEFIK_REPO,      running_traefik_version())):
        if not current:
            continue
        alert = _update_alert(key, product, current, latest_release(repo), seen)
        if alert:
            raised.append(alert)
    return raised
