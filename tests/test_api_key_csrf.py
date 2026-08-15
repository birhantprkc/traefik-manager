import hashlib

import pytest

from tests.conftest import tm

WRITE_ENDPOINTS = [
    ('/api/notifications/add',    {'message': 'from a script'}),
    ('/api/notifications/log',    {'message': 'from a script'}),
    ('/api/notifications/delete', {'ts': '2026-01-01 00:00:00'}),
    ('/api/notifications/clear',  {}),
]

KEY = 'tm-test-api-key'


@pytest.fixture
def keyed_client(monkeypatch):
    from core import settings as settings_mod
    real_load = settings_mod.load_settings

    def with_key():
        s = dict(real_load())
        s['api_keys'] = [{'name': 'test', 'hash': 'sha256:' + hashlib.sha256(KEY.encode()).hexdigest()}]
        return s

    monkeypatch.setattr(settings_mod, 'load_settings', with_key)
    monkeypatch.setattr(tm, 'load_settings', with_key, raising=False)
    from core import auth as auth_mod
    monkeypatch.setattr(auth_mod.settings_mod, 'load_settings', with_key)
    return tm.app.test_client()


@pytest.mark.parametrize('path,body', WRITE_ENDPOINTS)
def test_api_key_write_is_not_blocked_by_csrf(keyed_client, path, body):
    r = keyed_client.post(path, json=body, headers={'X-Api-Key': KEY})
    assert r.status_code != 403, (
        f'{path} rejected a valid API key with CSRF. API keys are documented to skip CSRF.')
    assert r.status_code < 500, f'{path} returned {r.status_code}'


@pytest.mark.parametrize('path,body', WRITE_ENDPOINTS)
def test_session_write_without_csrf_token_is_still_rejected(client, path, body):
    r = client.post(path, json=body)
    assert r.status_code == 403, f'{path} accepted a session write with no CSRF token'


@pytest.mark.parametrize('path,body', WRITE_ENDPOINTS)
def test_anonymous_write_is_rejected(anon_client, path, body):
    r = anon_client.post(path, json=body)
    assert r.status_code in (401, 403), f'{path} allowed an anonymous write'


def test_no_api_endpoint_calls_check_csrf_directly():
    import re
    src = open(tm.__file__.replace('.pyc', '.py')).read()
    lines = src.split('\n')
    offenders = []
    for i, line in enumerate(lines):
        if '_check_csrf()' not in line or line.strip().startswith('def '):
            continue
        for j in range(i, -1, -1):
            m = re.match(r"@app\.route\(\s*'([^']+)'", lines[j])
            if m:
                if m.group(1).startswith('/api/'):
                    offenders.append(m.group(1))
                break
    assert not offenders, (
        'these /api/ endpoints call _check_csrf() directly, which blocks API keys; '
        'use @csrf_protect instead: ' + ', '.join(sorted(set(offenders))))
