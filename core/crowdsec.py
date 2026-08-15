import hashlib
import os
import threading
from datetime import datetime, timedelta, timezone

import requests

from core import settings as settings_mod
from core.env import logger

_cs_jwt_cache = {'token': '', 'expiry': None}

CS_STREAM_RESYNC_SECONDS = 3600
_cs_stream_lock = threading.Lock()
_cs_stream_cache = {'fp': '', 'items': {}, 'synced': None, 'ready': False, 'streamable': True}

CS_CONNECT_TIMEOUT_DEFAULT = 5
CS_READ_TIMEOUT_DEFAULT = 20


def _cs_int_env(name: str, fallback: int, lo: int, hi: int) -> int:
    try:
        v = int(str(os.environ.get(name, '')).strip() or fallback)
    except ValueError:
        return fallback
    return max(lo, min(hi, v))


def cs_timeout():
    s = settings_mod.load_settings()
    try:
        read = int(str(s.get('crowdsec_read_timeout', '')).strip() or 0)
    except ValueError:
        read = 0
    if read <= 0:
        read = _cs_int_env('CROWDSEC_READ_TIMEOUT', CS_READ_TIMEOUT_DEFAULT, 1, 25)
    return (_cs_int_env('CROWDSEC_CONNECT_TIMEOUT', CS_CONNECT_TIMEOUT_DEFAULT, 1, 30),
            max(1, min(25, read)))


CS_ALERT_LIMIT_DEFAULT = 500


def cs_alert_limit() -> int:
    s = settings_mod.load_settings()
    try:
        v = int(str(s.get('crowdsec_alert_limit', '')).strip() or -1)
    except ValueError:
        v = -1
    if v < 0:
        v = _cs_int_env('CROWDSEC_ALERT_LIMIT', CS_ALERT_LIMIT_DEFAULT, 0, 100000)
    return max(0, min(100000, v))


def _cs_lapi_url() -> str:
    s = settings_mod.load_settings()
    return s.get('crowdsec_lapi_url', '').strip() or os.environ.get('CROWDSEC_LAPI_URL', '').strip()


def _cs_api_key() -> str:
    s = settings_mod.load_settings()
    return s.get('crowdsec_api_key', '').strip() or os.environ.get('CROWDSEC_API_KEY', '').strip()


def _cs_machine_id() -> str:
    s = settings_mod.load_settings()
    return s.get('crowdsec_machine_id', '').strip() or os.environ.get('CROWDSEC_MACHINE_ID', '').strip()


def _cs_machine_password() -> str:
    s = settings_mod.load_settings()
    return s.get('crowdsec_machine_password', '').strip() or os.environ.get('CROWDSEC_MACHINE_PASSWORD', '').strip()


def _cs_client_cert() -> str:
    s = settings_mod.load_settings()
    return s.get('crowdsec_client_cert', '').strip() or os.environ.get('CROWDSEC_CLIENT_CERT', '').strip()


def _cs_client_key() -> str:
    s = settings_mod.load_settings()
    return s.get('crowdsec_client_key', '').strip() or os.environ.get('CROWDSEC_CLIENT_KEY', '').strip()


def _cs_ca_cert() -> str:
    s = settings_mod.load_settings()
    return s.get('crowdsec_ca_cert', '').strip() or os.environ.get('CROWDSEC_CA_CERT', '').strip()


def _cs_has_cert() -> bool:
    return bool(_cs_client_cert() and _cs_client_key())


def _cs_tls_kwargs() -> dict:
    kw = {}
    if _cs_has_cert():
        kw['cert'] = (_cs_client_cert(), _cs_client_key())
    ca = _cs_ca_cert()
    if ca:
        kw['verify'] = ca
    return kw


def _cs_has_machine() -> bool:
    return bool(_cs_machine_id() and _cs_machine_password()) or _cs_has_cert()


class CrowdSecUnavailable(Exception):
    pass


def _cs_request_strict(method: str, path: str, lapi: str = None, key: str = None, **kwargs):
    if lapi is None:
        lapi = _cs_lapi_url()
    if key is None:
        key = _cs_api_key()
    lapi = (lapi or '').rstrip('/')
    if not lapi or not (key or _cs_has_cert()):
        raise CrowdSecUnavailable('CrowdSec LAPI URL, bouncer API key or client certificate is not set')
    headers = {'Accept': 'application/json'}
    if key:
        headers['X-Api-Key'] = key
    try:
        resp = requests.request(method, f"{lapi}{path}",
                                headers=headers,
                                timeout=cs_timeout(), **_cs_tls_kwargs(), **kwargs)
        resp.raise_for_status()
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        logger.warning(f"CrowdSec LAPI error {method} {path}: {e}")
        raise CrowdSecUnavailable(f'LAPI answered HTTP {status} on {path}') from e
    except Exception as e:
        logger.warning(f"CrowdSec LAPI error {method} {path}: {e}")
        raise CrowdSecUnavailable(f'CrowdSec LAPI unreachable: {e}') from e
    return resp.json() if resp.content else None


def _cs_request(method: str, path: str, lapi: str = None, key: str = None, **kwargs):
    try:
        return _cs_request_strict(method, path, lapi=lapi, key=key, **kwargs)
    except CrowdSecUnavailable:
        return None


def _cs_jwt(lapi: str = None) -> str:
    if lapi is None:
        lapi = _cs_lapi_url()
    lapi = lapi.rstrip('/')
    mid  = _cs_machine_id()
    pw   = _cs_machine_password()
    if not (lapi and ((mid and pw) or _cs_has_cert())):
        return ''
    now = datetime.now(timezone.utc)
    if _cs_jwt_cache['token'] and _cs_jwt_cache['expiry'] and now < _cs_jwt_cache['expiry']:
        return _cs_jwt_cache['token']
    payload = {'scenarios': []}
    if mid and pw:
        payload['machine_id'] = mid
        payload['password'] = pw
    try:
        resp = requests.post(f"{lapi}/v1/watchers/login",
                             json=payload,
                             timeout=cs_timeout(), **_cs_tls_kwargs())
        resp.raise_for_status()
        body  = resp.json() or {}
        token = body.get('token', '')
        if not token:
            return ''
        _cs_jwt_cache['token'] = token
        try:
            exp = datetime.fromisoformat(str(body.get('expire', '')).replace('Z', '+00:00'))
            _cs_jwt_cache['expiry'] = exp - timedelta(minutes=2)
        except Exception:
            _cs_jwt_cache['expiry'] = now + timedelta(minutes=58)
        return token
    except Exception as e:
        logger.warning(f"CrowdSec machine login failed: {e}")
        return ''


def _cs_machine_request(method: str, path: str, **kwargs):
    lapi  = _cs_lapi_url().rstrip('/')
    token = _cs_jwt(lapi)
    if not (lapi and token):
        return None
    try:
        resp = requests.request(method, f"{lapi}{path}",
                                headers={'Authorization': f'Bearer {token}', 'Accept': 'application/json'},
                                timeout=cs_timeout(), **_cs_tls_kwargs(), **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except Exception as e:
        logger.warning(f"CrowdSec machine request error {method} {path}: {e}")
        return None


def _cs_fingerprint() -> str:
    raw = '|'.join([_cs_lapi_url(), _cs_api_key(), _cs_client_cert(), _cs_ca_cert()])
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]


def cs_stream_reset():
    with _cs_stream_lock:
        _cs_stream_cache.update({'fp': '', 'items': {}, 'synced': None, 'ready': False, 'streamable': True})


def _cs_apply_stream(payload, replace: bool):
    items = {} if replace else dict(_cs_stream_cache['items'])
    for d in (payload.get('new') or []):
        did = d.get('id')
        if did is not None:
            items[str(did)] = d
    for d in (payload.get('deleted') or []):
        did = d.get('id')
        if did is not None:
            items.pop(str(did), None)
        else:
            val = d.get('value')
            if val:
                for k, v in list(items.items()):
                    if v.get('value') == val and v.get('type') == d.get('type'):
                        items.pop(k, None)
    return items


def cs_decisions_stream(force_full: bool = False):
    """Active decisions via /v1/decisions/stream, cached with deltas.

    Returns (decisions, mode) where mode is 'full', 'delta' or 'cache'.
    Raises CrowdSecUnavailable only when there is no usable cached answer.
    """
    fp = _cs_fingerprint()
    now = datetime.now(timezone.utc)
    with _cs_stream_lock:
        c = _cs_stream_cache
        stale = bool(c['synced'] and (now - c['synced']).total_seconds() > CS_STREAM_RESYNC_SECONDS)
        full = force_full or c['fp'] != fp or not c['ready'] or stale
        path = '/v1/decisions/stream?startup=true' if full else '/v1/decisions/stream'
        try:
            payload = _cs_request_strict('GET', path)
        except CrowdSecUnavailable:
            if c['ready'] and c['fp'] == fp:
                return list(c['items'].values()), 'cache'
            raise
        if not isinstance(payload, dict):
            raise CrowdSecUnavailable('LAPI stream returned an unexpected payload')
        if full:
            c['items'] = _cs_apply_stream(payload, True)
        else:
            c['items'] = _cs_apply_stream(payload, False)
        c['fp'] = fp
        c['synced'] = now
        c['ready'] = True
        return list(c['items'].values()), ('full' if full else 'delta')
