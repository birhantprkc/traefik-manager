"""CrowdSec LAPI client: decisions, alerts and machine login."""
import os
from datetime import datetime, timedelta, timezone

import requests

from core import settings as settings_mod
from core.env import logger

_cs_jwt_cache = {'token': '', 'expiry': None}


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
    """The LAPI could not be reached or refused the read. Never the same as an empty result."""


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
                                timeout=5, **_cs_tls_kwargs(), **kwargs)
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
                             timeout=5, **_cs_tls_kwargs())
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
                                timeout=5, **_cs_tls_kwargs(), **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except Exception as e:
        logger.warning(f"CrowdSec machine request error {method} {path}: {e}")
        return None
