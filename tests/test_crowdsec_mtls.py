import pytest

from tests.conftest import tm
from core import crowdsec as cs


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for var in ('CROWDSEC_LAPI_URL', 'CROWDSEC_API_KEY', 'CROWDSEC_MACHINE_ID',
                'CROWDSEC_MACHINE_PASSWORD', 'CROWDSEC_CLIENT_CERT',
                'CROWDSEC_CLIENT_KEY', 'CROWDSEC_CA_CERT'):
        monkeypatch.delenv(var, raising=False)
    cs._cs_jwt_cache['token'] = ''
    cs._cs_jwt_cache['expiry'] = None
    yield
    cs._cs_jwt_cache['token'] = ''
    cs._cs_jwt_cache['expiry'] = None


def _set_cert(monkeypatch, ca=False):
    monkeypatch.setenv('CROWDSEC_CLIENT_CERT', '/certs/client.crt')
    monkeypatch.setenv('CROWDSEC_CLIENT_KEY', '/certs/client.key')
    if ca:
        monkeypatch.setenv('CROWDSEC_CA_CERT', '/certs/ca.crt')


class _Resp:
    def __init__(self, payload):
        self._payload = payload
        self.content = b'x'
        self.status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_not_configured_by_default():
    assert not cs._cs_has_cert()
    assert not cs._cs_has_machine()
    assert cs._cs_tls_kwargs() == {}


def test_cert_pair_counts_as_configured(monkeypatch):
    _set_cert(monkeypatch)
    assert cs._cs_has_cert()
    assert cs._cs_has_machine()


def test_cert_alone_is_not_enough(monkeypatch):
    monkeypatch.setenv('CROWDSEC_CLIENT_CERT', '/certs/client.crt')
    assert not cs._cs_has_cert()


def test_tls_kwargs_cert_and_ca(monkeypatch):
    _set_cert(monkeypatch, ca=True)
    kw = cs._cs_tls_kwargs()
    assert kw['cert'] == ('/certs/client.crt', '/certs/client.key')
    assert kw['verify'] == '/certs/ca.crt'


def test_ca_alone_still_verifies(monkeypatch):
    monkeypatch.setenv('CROWDSEC_CA_CERT', '/certs/ca.crt')
    assert cs._cs_tls_kwargs() == {'verify': '/certs/ca.crt'}


def test_strict_request_requires_key_or_cert(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    with pytest.raises(cs.CrowdSecUnavailable):
        cs._cs_request_strict('GET', '/v1/decisions')


def test_strict_request_cert_only_sends_no_api_key(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    _set_cert(monkeypatch, ca=True)
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(kwargs, method=method, url=url)
        return _Resp([])

    monkeypatch.setattr(cs.requests, 'request', fake_request)
    cs._cs_request_strict('GET', '/v1/decisions')
    assert 'X-Api-Key' not in seen['headers']
    assert seen['cert'] == ('/certs/client.crt', '/certs/client.key')
    assert seen['verify'] == '/certs/ca.crt'


def test_strict_request_key_still_sent_alongside_cert(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    monkeypatch.setenv('CROWDSEC_API_KEY', 'bouncer-key')
    _set_cert(monkeypatch)
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(kwargs)
        return _Resp([])

    monkeypatch.setattr(cs.requests, 'request', fake_request)
    cs._cs_request_strict('GET', '/v1/decisions')
    assert seen['headers']['X-Api-Key'] == 'bouncer-key'
    assert seen['cert'] == ('/certs/client.crt', '/certs/client.key')


def test_jwt_cert_only_omits_credentials(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    _set_cert(monkeypatch, ca=True)
    seen = {}

    def fake_post(url, **kwargs):
        seen.update(kwargs, url=url)
        return _Resp({'token': 'tok', 'expire': '2099-01-01T00:00:00Z'})

    monkeypatch.setattr(cs.requests, 'post', fake_post)
    assert cs._cs_jwt() == 'tok'
    assert 'machine_id' not in seen['json']
    assert 'password' not in seen['json']
    assert seen['cert'] == ('/certs/client.crt', '/certs/client.key')
    assert seen['verify'] == '/certs/ca.crt'


def test_jwt_sends_credentials_when_set(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    monkeypatch.setenv('CROWDSEC_MACHINE_ID', 'tm')
    monkeypatch.setenv('CROWDSEC_MACHINE_PASSWORD', 'pw')
    seen = {}

    def fake_post(url, **kwargs):
        seen.update(kwargs)
        return _Resp({'token': 'tok', 'expire': '2099-01-01T00:00:00Z'})

    monkeypatch.setattr(cs.requests, 'post', fake_post)
    assert cs._cs_jwt() == 'tok'
    assert seen['json']['machine_id'] == 'tm'
    assert seen['json']['password'] == 'pw'


def test_jwt_refuses_without_creds_or_cert(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    assert cs._cs_jwt() == ''


def test_machine_request_carries_tls_kwargs(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    _set_cert(monkeypatch, ca=True)
    monkeypatch.setattr(cs, '_cs_jwt', lambda lapi=None: 'tok')
    seen = {}

    def fake_request(method, url, **kwargs):
        seen.update(kwargs)
        return _Resp([])

    monkeypatch.setattr(cs.requests, 'request', fake_request)
    assert cs._cs_machine_request('GET', '/v1/alerts') == []
    assert seen['cert'] == ('/certs/client.crt', '/certs/client.key')
    assert seen['verify'] == '/certs/ca.crt'


def test_decisions_endpoint_gate_accepts_cert_only(monkeypatch, client):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    _set_cert(monkeypatch)
    monkeypatch.setattr(tm, '_cs_request_strict', lambda *a, **k: [])
    resp = client.get('/api/crowdsec/decisions')
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_decisions_endpoint_still_gated_without_any_auth(monkeypatch, client):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'https://lapi:8080')
    resp = client.get('/api/crowdsec/decisions')
    assert resp.status_code == 503


def test_settings_roundtrip_cert_paths():
    from core import settings as settings_mod
    settings_mod.save_settings(
        ['example.com'], 'letsencrypt', 'http://traefik:8080',
        crowdsec_client_cert='/certs/c.crt',
        crowdsec_client_key='/certs/c.key',
        crowdsec_ca_cert='/certs/ca.crt',
    )
    s = settings_mod.load_settings()
    assert s['crowdsec_client_cert'] == '/certs/c.crt'
    assert s['crowdsec_client_key'] == '/certs/c.key'
    assert s['crowdsec_ca_cert'] == '/certs/ca.crt'
    settings_mod.save_settings(
        ['example.com'], 'letsencrypt', 'http://traefik:8080',
        crowdsec_client_cert='', crowdsec_client_key='', crowdsec_ca_cert='',
    )
