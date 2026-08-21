"""In-app notification log and webhook delivery."""
import os
import threading
import time
from collections import deque
from contextlib import contextmanager

import requests
from ruamel.yaml import YAML as SafeYAML

from core import env
from core import settings as settings_mod
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

def _fire_webhook(type_: str, msg: str, ts: str):
    s   = settings_mod.load_settings()
    url = s.get('webhook_url', '').strip()
    if not url:
        return
    wtype    = s.get('webhook_type', 'discord')
    username = s.get('webhook_username', '')
    password = s.get('webhook_password', '')
    try:
        _send_webhook(url, wtype, type_, msg, ts, username, password)
    except Exception as e:
        logger.warning(f"Webhook delivery failed: {e}")

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


def add_notification(type_, msg, webhook=True):
    msg = str(msg or '').strip()
    if not msg:
        return False
    now   = time.time()
    entry = {'ts': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)), 'type': type_, 'msg': msg}
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
        threading.Thread(target=_fire_webhook, args=(type_, msg, entry['ts']), daemon=True).start()
    return True
