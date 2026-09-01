import pytest


class _Resp:
    status_code = 204


@pytest.fixture
def ping(client, monkeypatch):
    import app as tm
    reached = []

    def fake_head(target, **kw):
        reached.append(target)
        if 'good' in target:
            return _Resp()
        raise OSError('primary is down')

    monkeypatch.setattr(tm.requests, 'head', fake_head)
    return reached


def test_a_blocked_fallback_is_never_requested(ping, monkeypatch):
    import app as tm
    monkeypatch.setattr(tm, '_ssrf_ok', lambda u: 'blocked' not in u)
    r = client_get(tm, 'http://allowed.example', 'http://blocked.example')
    assert not r.get_json().get('via_target'), 'a blocked fallback must not be used'
    assert 'http://blocked.example' not in ping, \
        'the fallback reached an address the guard refuses'


def test_an_allowed_fallback_still_works(ping, monkeypatch):
    import app as tm
    monkeypatch.setattr(tm, '_ssrf_ok', lambda u: True)
    r = client_get(tm, 'http://bad.example', 'http://good.example')
    assert r.get_json().get('via_target') is True


def test_link_local_is_refused_by_the_guard():
    import app as tm
    assert not tm._ssrf_ok('http://169.254.169.254/latest/meta-data/'), \
        'cloud metadata is link local and must never pass'
    assert not tm._ssrf_ok('http://[fe80::1]/')


def test_the_addresses_this_tool_exists_to_reach_still_pass():
    import app as tm
    for url in ('http://10.0.0.5:8080', 'http://172.17.0.2:8080',
                'http://192.168.1.10:8080', 'http://127.0.0.1:8080'):
        assert tm._ssrf_ok(url), (
            f'{url} must stay reachable: the default Docker config points at a private '
            f'address and the documented systemd config points at loopback')


_client = None


def client_get(tm, url, fallback):
    return _client.get(f'/api/ping?url={url}&fallback={fallback}')


@pytest.fixture(autouse=True)
def _bind(client):
    global _client
    _client = client
    yield
    _client = None
