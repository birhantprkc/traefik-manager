import pytest

from core import crowdsec as cs

CS_VARS = ('CROWDSEC_LAPI_URL', 'CROWDSEC_API_KEY', 'CROWDSEC_MACHINE_ID',
           'CROWDSEC_MACHINE_PASSWORD', 'CROWDSEC_CLIENT_CERT',
           'CROWDSEC_CLIENT_KEY', 'CROWDSEC_CA_CERT')


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for var in CS_VARS:
        monkeypatch.delenv(var, raising=False)
    cs._cs_jwt_cache['token'] = ''
    cs._cs_jwt_cache['expiry'] = None
    yield
    cs._cs_jwt_cache['token'] = ''
    cs._cs_jwt_cache['expiry'] = None


def _machine(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'http://lapi:8080')
    monkeypatch.setenv('CROWDSEC_MACHINE_ID', 'manager')
    monkeypatch.setenv('CROWDSEC_MACHINE_PASSWORD', 'secret')


def _alert(scope='Ip', value='1.2.3.4', decisions=None, scenario='test/bf'):
    alert = {'id': 1, 'scenario': scenario, 'created_at': '2026-08-21T10:00:00Z',
             'source': {'scope': scope, 'value': value}}
    if decisions is not None:
        alert['decisions'] = decisions
    return alert


def _boom(*args, **kwargs):
    raise AssertionError('the LAPI must not be called without machine credentials')


def test_no_machine_credentials_returns_empty_without_calling_the_lapi(monkeypatch):
    monkeypatch.setattr(cs, '_cs_machine_request', _boom)
    assert cs.poll_local_alerts() == []


def test_a_bouncer_key_alone_is_not_enough(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'http://lapi:8080')
    monkeypatch.setenv('CROWDSEC_API_KEY', 'bouncer')
    monkeypatch.setattr(cs, '_cs_machine_request', _boom)
    assert cs.poll_local_alerts() == []


def test_the_query_asks_for_the_local_origin_and_window(monkeypatch):
    _machine(monkeypatch)
    seen = []

    def fake(method, path, **kw):
        seen.append((method, path))
        return []

    monkeypatch.setattr(cs, '_cs_machine_request', fake)
    assert cs.poll_local_alerts() == []
    method, path = seen[0]
    assert method == 'GET'
    assert path.startswith('/v1/alerts?')
    for part in ('since=15m', 'origin=crowdsec', 'with_decisions=false', 'limit=200'):
        assert part in path


def test_a_custom_window_is_passed_through(monkeypatch):
    _machine(monkeypatch)
    seen = []

    def fake(method, path, **kw):
        seen.append(path)
        return []

    monkeypatch.setattr(cs, '_cs_machine_request', fake)
    cs.poll_local_alerts(since='2h')
    assert 'since=2h' in seen[0]


def test_capi_and_list_alerts_are_dropped_again_in_python(monkeypatch):
    _machine(monkeypatch)
    payload = [
        _alert(scenario='local/ssh-bf'),
        _alert(scope='CAPI', value='', scenario='update : +2/-1 IPs'),
        _alert(scope='lists:firehol_cruzit_web_attacks', value='9.9.9.9'),
        _alert(scope='Ip', value='5.5.5.5', decisions=[{'origin': 'CAPI'}]),
        _alert(scope='Range', value='10.0.0.0/24', scenario='local/http-probing'),
    ]
    monkeypatch.setattr(cs, '_cs_machine_request', lambda m, p, **kw: payload)
    out = cs.poll_local_alerts()
    assert [a['scenario'] for a in out] == ['local/ssh-bf', 'local/http-probing']


def test_alerts_with_local_decisions_are_kept(monkeypatch):
    _machine(monkeypatch)
    payload = [_alert(decisions=[{'origin': 'crowdsec', 'type': 'ban'}])]
    monkeypatch.setattr(cs, '_cs_machine_request', lambda m, p, **kw: payload)
    assert len(cs.poll_local_alerts()) == 1


def test_an_unreachable_lapi_returns_empty_rather_than_raising(monkeypatch):
    _machine(monkeypatch)
    monkeypatch.setattr(cs, '_cs_machine_request', lambda m, p, **kw: None)
    assert cs.poll_local_alerts() == []


def test_a_junk_payload_returns_empty(monkeypatch):
    _machine(monkeypatch)
    monkeypatch.setattr(cs, '_cs_machine_request', lambda m, p, **kw: {'message': 'nope'})
    assert cs.poll_local_alerts() == []


def test_non_dict_rows_are_skipped(monkeypatch):
    _machine(monkeypatch)
    monkeypatch.setattr(cs, '_cs_machine_request', lambda m, p, **kw: ['x', None, _alert()])
    assert len(cs.poll_local_alerts()) == 1
