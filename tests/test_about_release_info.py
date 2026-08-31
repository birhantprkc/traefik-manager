import pytest

import core.updates as updates


@pytest.fixture(autouse=True)
def _clear_cache():
    updates._release_cache.clear()
    yield
    updates._release_cache.clear()


class _Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or {}

    def json(self):
        return self._payload


def test_release_info_is_cached_so_a_page_load_is_not_a_github_call(monkeypatch):
    calls = []

    def fake_get(url, **kw):
        calls.append(url)
        return _Resp(200, {'tag_name': 'v9.9.9', 'html_url': 'https://x', 'body': 'notes'})

    monkeypatch.setattr(updates.requests, 'get', fake_get)
    for _ in range(5):
        info = updates.release_info('owner/repo')
    assert len(calls) == 1, 'five reads must not be five GitHub requests'
    assert info['tag'] == '9.9.9'
    assert info['notes'] == 'notes'


def test_a_rate_limit_is_reported_not_swallowed(monkeypatch):
    monkeypatch.setattr(updates.requests, 'get', lambda url, **kw: _Resp(403))
    info = updates.release_info('owner/repo')
    assert info['tag'] == ''
    assert 'rate limited' in info['error']


def test_a_stale_hit_survives_a_later_failure(monkeypatch):
    monkeypatch.setattr(updates.requests, 'get',
                        lambda url, **kw: _Resp(200, {'tag_name': 'v1.0.0'}))
    assert updates.release_info('owner/repo')['tag'] == '1.0.0'
    updates._release_cache['owner/repo'] = (0, updates._release_cache['owner/repo'][1], 0)
    monkeypatch.setattr(updates.requests, 'get', lambda url, **kw: _Resp(403))
    assert updates.release_info('owner/repo')['tag'] == '1.0.0'


def test_a_network_error_does_not_raise(monkeypatch):
    def boom(url, **kw):
        raise OSError('no route to host')
    monkeypatch.setattr(updates.requests, 'get', boom)
    info = updates.release_info('owner/repo')
    assert info['tag'] == ''
    assert info['error']


def test_the_version_endpoint_carries_the_release_fields(client, monkeypatch):
    monkeypatch.setattr(updates.requests, 'get', lambda url, **kw: _Resp(
        200, {'tag_name': 'v5.5.5', 'html_url': 'https://rel', 'body': '## notes'}))
    d = client.get('/api/manager/version').get_json()
    for key in ('version', 'latest', 'release_url', 'release_notes',
                'release_error', 'traefik_latest', 'traefik_running'):
        assert key in d, key
    assert d['latest'] == '5.5.5'
    assert d['release_url'] == 'https://rel'
