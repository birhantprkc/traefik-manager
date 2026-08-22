"""In-app notification log and webhook delivery."""
import json
import os
import threading
import time
from collections import deque
from contextlib import contextmanager

import requests
from ruamel.yaml import YAML as SafeYAML

from core import env
from core import settings as settings_mod
from core import notify_providers as providers
from core.env import logger

try:
    import fcntl
except ImportError:
    fcntl = None

MAX_ENTRIES = 200

_notifications = deque(maxlen=MAX_ENTRIES)
_notif_lock    = threading.Lock()


def _lock_path():
    return env.NOTIFICATIONS_PATH + '.lock'


@contextmanager
def _file_lock():
    fh = None
    if fcntl is not None:
        try:
            fh = open(_lock_path(), 'a+')
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except Exception:
            if fh is not None:
                try:
                    fh.close()
                except Exception:
                    pass
            fh = None
    try:
        yield
    finally:
        if fh is not None:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                fh.close()
            except Exception:
                pass


def _read_file():
    try:
        with open(env.NOTIFICATIONS_PATH, 'r') as f:
            data = SafeYAML(typ='safe').load(f) or []
        return [e for e in data if isinstance(e, dict)]
    except Exception:
        return []


def _write_file(entries):
    from core.config import _replace_or_copy
    path = env.NOTIFICATIONS_PATH
    tmp  = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp, 'w') as f:
            SafeYAML(typ='safe').dump(list(entries), f)
        _replace_or_copy(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _sync(entries):
    _notifications.clear()
    for e in entries[-MAX_ENTRIES:]:
        _notifications.append(e)


def _send_webhook(url: str, wtype: str, type_: str, msg: str, ts: str, username: str = '', password: str = ''):
    color_map = {'warning': 0xf0a500, 'error': 0xf85149, 'info': 0x58a6ff, 'success': 0x3fb950}
    color = color_map.get(type_, 0x58a6ff)
    tag_map = {'warning': 'warning', 'error': 'rotating_light', 'success': 'white_check_mark', 'info': 'information_source'}
    auth = (username, password) if username else None
    if wtype == 'discord':
        payload = {'embeds': [{'title': msg, 'color': color, 'footer': {'text': f'Traefik Manager - {ts}'}}]}
        requests.post(url, json=payload, timeout=5, auth=auth)
    elif wtype == 'slack':
        icon = {'warning': ':warning:', 'error': ':x:', 'success': ':white_check_mark:', 'info': ':information_source:'}.get(type_, ':bell:')
        requests.post(url, json={'text': f'{icon} *Traefik Manager* - {msg}'}, timeout=5, auth=auth)
    elif wtype == 'ntfy':
        headers = {
            'X-Title': 'Traefik Manager',
            'X-Priority': '4' if type_ in ('warning', 'error') else '3',
            'X-Tags': tag_map.get(type_, 'bell'),
        }
        requests.post(url, data=msg.encode('utf-8'), headers=headers, timeout=5, auth=auth)
    else:
        requests.post(url, json={'event': type_, 'message': msg, 'timestamp': ts}, timeout=5, auth=auth)

QUEUE_MAX = 500

CATEGORY_LABELS = {
    'config': 'Config', 'backup': 'Backups', 'security': 'Security',
    'traefik': 'Traefik', 'certs': 'Certificates', 'crowdsec': 'CrowdSec',
    'agent': 'Agents', 'update': 'Updates',
}


def _queue_path():
    return os.path.join(os.path.dirname(env.NOTIFICATIONS_PATH), 'notification_queue.json')


def _queue_read():
    try:
        with open(_queue_path(), 'r') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _queue_write(data):
    path = _queue_path()
    tmp = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp, 'w') as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except Exception:
        logger.exception("Failed to write the notification queue")
        try:
            os.unlink(tmp)
        except Exception:
            pass


def queue_add(channel_id, type_, msg, ts, category):
    """Hold a message for a channel that is in quiet hours or on a digest."""
    if not channel_id:
        return
    with _notif_lock, _file_lock():
        q = _queue_read()
        held = q.setdefault(channel_id, {'items': [], 'dropped': 0})
        if len(held['items']) >= QUEUE_MAX:
            held['dropped'] = held.get('dropped', 0) + 1
        else:
            held['items'].append({'type': type_, 'msg': msg, 'ts': ts, 'category': category})
        _queue_write(q)


def build_report(items, dropped=0) -> str:
    """Collapse held messages into one report, grouped by category.

    Not a replay. Three CrowdSec rollups become one CrowdSec line, so the end of
    a quiet window is a summary rather than a burst.
    """
    if not items:
        return ''
    order = [c for c in CATEGORY_LABELS if any(i.get('category') == c for i in items)]
    lines = []
    for cat in order:
        rows = [i for i in items if i.get('category') == cat]
        label = CATEGORY_LABELS.get(cat, cat.title())
        if len(rows) == 1:
            lines.append(f"{label}: {rows[0]['msg']}")
            continue
        lines.append(f"{label}: {len(rows)} events, latest {rows[-1]['msg']}")
    if dropped:
        lines.append(f"and {dropped} more")
    span = f"{items[0]['ts']} to {items[-1]['ts']}"
    return f"Summary {span}\n" + "\n".join(lines)


def flush_queue(channel_id=None, force=False) -> int:
    """Send one collapsed report per channel whose window has ended."""
    try:
        channels = settings_mod.load_settings().get('notification_channels', [])
    except Exception:
        return 0
    by_id = {c.get('id'): c for c in channels}
    sent = 0
    with _notif_lock, _file_lock():
        q = _queue_read()
        for cid in list(q):
            if channel_id and cid != channel_id:
                continue
            ch = by_id.get(cid)
            if not ch:
                del q[cid]
                continue
            if not force and _in_quiet_hours(ch.get('quiet_hours', '')):
                continue
            held = q.get(cid) or {}
            items = held.get('items') or []
            if not items:
                del q[cid]
                continue
            report = build_report(items, held.get('dropped', 0))
            worst = max(items, key=lambda r: SEVERITY_RANK.get(r.get('type'), 0))
            try:
                _deliver(ch, worst.get('type', 'info'), report, items[-1]['ts'])
                sent += 1
            except Exception:
                logger.exception("Queue flush delivery raised")
            del q[cid]
        _queue_write(q)
    return sent


SEVERITY_RANK = {'info': 0, 'success': 0, 'warning': 1, 'error': 2}


def _in_quiet_hours(window: str, when=None) -> bool:
    """True if `when` falls inside a HH:MM-HH:MM window, wrapping past midnight."""
    if not window or '-' not in window:
        return False
    try:
        start_s, end_s = window.split('-', 1)
        sh, sm = [int(x) for x in start_s.strip().split(':')]
        eh, em = [int(x) for x in end_s.strip().split(':')]
    except Exception:
        return False
    t = time.localtime(when if when is not None else time.time())
    cur   = t.tm_hour * 60 + t.tm_min
    start = sh * 60 + sm
    end   = eh * 60 + em
    if start == end:
        return False
    if start < end:
        return start <= cur < end
    return cur >= start or cur < end


def _wants(channel: dict, type_: str, category: str) -> bool:
    if not channel.get('enabled', True):
        return False
    cats = channel.get('categories') or []
    if cats and category not in cats:
        return False
    floor = SEVERITY_RANK.get(channel.get('min_severity', 'info'), 0)
    return SEVERITY_RANK.get(type_, 0) >= floor


def _deliver(channel: dict, type_: str, msg: str, ts: str):
    missing = providers.missing_fields(channel)
    if missing:
        logger.warning(f"Channel {channel.get('name')} is missing {', '.join(missing)}")
        return
    ok, err = providers.send(channel, type_, 'Traefik Manager', msg, ts)
    if not ok:
        logger.warning(f"Channel {channel.get('name')} delivery failed: {err}")


def _fire_webhook(type_: str, msg: str, ts: str, category: str = 'config'):
    """Route one notification to every channel that wants it."""
    try:
        channels = settings_mod.load_settings().get('notification_channels', [])
    except Exception:
        return
    for ch in channels:
        try:
            if not _wants(ch, type_, category):
                continue
            quiet = _in_quiet_hours(ch.get('quiet_hours', ''))
            breaks = ch.get('break_through') and type_ == 'error'
            if quiet and not breaks:
                queue_add(ch.get('id', ''), type_, msg, ts, category)
                continue
            if ch.get('digest', 'immediate') != 'immediate':
                queue_add(ch.get('id', ''), type_, msg, ts, category)
                continue
            _deliver(ch, type_, msg, ts)
        except Exception:
            logger.exception("Channel delivery raised")


def _load_notifications():
    with _notif_lock, _file_lock():
        _sync(_read_file())

def _save_notifications_bg():
    try:
        with _notif_lock, _file_lock():
            _write_file(list(_notifications))
    except Exception:
        logger.exception("Failed to save notifications")

DEDUPE_WINDOW = 8


def _recently_logged(entries, msg, now):
    for entry in reversed(entries):
        try:
            age = now - time.mktime(time.strptime(entry.get('ts', ''), "%Y-%m-%d %H:%M:%S"))
        except (ValueError, TypeError):
            continue
        if age > DEDUPE_WINDOW:
            return False
        if entry.get('msg') == msg:
            return True
    return False


def get_notifications():
    """Newest first. Reads the file so every worker sees the same list."""
    with _notif_lock, _file_lock():
        entries = _read_file()
        _sync(entries)
        return list(reversed(entries[-MAX_ENTRIES:]))


def delete_notification(ts):
    with _notif_lock, _file_lock():
        entries = _read_file()
        for i, entry in enumerate(entries):
            if entry.get('ts') == ts:
                del entries[i]
                break
        _write_file(entries)
        _sync(entries)
    return True


def clear_notifications():
    with _notif_lock, _file_lock():
        _write_file([])
        _sync([])
    return True


def add_notification(type_, msg, category='config', webhook=True):
    msg = str(msg or '').strip()
    if not msg:
        return False
    now   = time.time()
    entry = {'ts': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
             'type': type_, 'msg': msg, 'category': category}
    try:
        with _notif_lock, _file_lock():
            entries = _read_file()
            if _recently_logged(entries, msg, now):
                _sync(entries)
                return False
            entries.append(entry)
            entries = entries[-MAX_ENTRIES:]
            _write_file(entries)
            _sync(entries)
    except Exception:
        logger.exception("Failed to store notification")
        return False
    if webhook:
        threading.Thread(target=_fire_webhook,
                         args=(type_, msg, entry['ts'], category), daemon=True).start()
    return True
