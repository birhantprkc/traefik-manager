import pytest

from core import crowdsec as cs


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for var in ('CROWDSEC_LAPI_URL', 'CROWDSEC_API_KEY', 'CROWDSEC_READ_TIMEOUT',
                'CROWDSEC_CONNECT_TIMEOUT', 'CROWDSEC_ALERT_LIMIT',
                'CROWDSEC_CLIENT_CERT', 'CROWDSEC_CLIENT_KEY', 'CROWDSEC_CA_CERT'):
        monkeypatch.delenv(var, raising=False)
    cs.cs_stream_reset()
    yield
    cs.cs_stream_reset()


def test_timeout_is_a_connect_read_tuple():
    t = cs.cs_timeout()
    assert isinstance(t, tuple) and len(t) == 2
    assert t[0] == cs.CS_CONNECT_TIMEOUT_DEFAULT
    assert t[1] == cs.CS_READ_TIMEOUT_DEFAULT


def test_read_timeout_env_override(monkeypatch):
    monkeypatch.setenv('CROWDSEC_READ_TIMEOUT', '18')
    assert cs.cs_timeout()[1] == 18


def test_read_timeout_never_exceeds_the_gunicorn_worker_budget(monkeypatch):
    monkeypatch.setenv('CROWDSEC_READ_TIMEOUT', '900')
    assert cs.cs_timeout()[1] == 25


def test_read_timeout_rejects_garbage(monkeypatch):
    monkeypatch.setenv('CROWDSEC_READ_TIMEOUT', 'soon')
    assert cs.cs_timeout()[1] == cs.CS_READ_TIMEOUT_DEFAULT


def test_alert_limit_default_is_bounded():
    assert cs.cs_alert_limit() == cs.CS_ALERT_LIMIT_DEFAULT
    assert cs.cs_alert_limit() > 0


def test_alert_limit_env_override(monkeypatch):
    monkeypatch.setenv('CROWDSEC_ALERT_LIMIT', '50')
    assert cs.cs_alert_limit() == 50


def test_alert_limit_zero_means_unbounded_opt_out(monkeypatch):
    monkeypatch.setenv('CROWDSEC_ALERT_LIMIT', '0')
    assert cs.cs_alert_limit() == 0


def _payload(new=None, deleted=None):
    return {'new': new or [], 'deleted': deleted or []}


def _dec(i, value, origin='crowdsec'):
    return {'id': i, 'value': value, 'origin': origin, 'type': 'ban',
            'scenario': 'test', 'scope': 'Ip', 'duration': '1h'}


def test_stream_startup_then_delta(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'http://lapi:8080')
    monkeypatch.setenv('CROWDSEC_API_KEY', 'k')
    calls = []

    def fake(method, path, **kw):
        calls.append(path)
        if 'startup=true' in path:
            return _payload(new=[_dec(1, '1.1.1.1'), _dec(2, '2.2.2.2')])
        return _payload(new=[_dec(3, '3.3.3.3')], deleted=[_dec(1, '1.1.1.1')])

    monkeypatch.setattr(cs, '_cs_request_strict', fake)

    rows, mode = cs.cs_decisions_stream()
    assert mode == 'full'
    assert sorted(r['value'] for r in rows) == ['1.1.1.1', '2.2.2.2']
    assert 'startup=true' in calls[0]

    rows, mode = cs.cs_decisions_stream()
    assert mode == 'delta'
    assert 'startup=true' not in calls[1]
    assert sorted(r['value'] for r in rows) == ['2.2.2.2', '3.3.3.3']


def test_delta_failure_serves_the_cache_instead_of_erroring(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'http://lapi:8080')
    monkeypatch.setenv('CROWDSEC_API_KEY', 'k')
    state = {'n': 0}

    def fake(method, path, **kw):
        state['n'] += 1
        if state['n'] == 1:
            return _payload(new=[_dec(1, '1.1.1.1')])
        raise cs.CrowdSecUnavailable('read timed out')

    monkeypatch.setattr(cs, '_cs_request_strict', fake)
    rows, mode = cs.cs_decisions_stream()
    assert mode == 'full' and len(rows) == 1

    rows, mode = cs.cs_decisions_stream()
    assert mode == 'cache'
    assert [r['value'] for r in rows] == ['1.1.1.1']


def test_startup_failure_with_no_cache_raises(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'http://lapi:8080')
    monkeypatch.setenv('CROWDSEC_API_KEY', 'k')

    def fake(method, path, **kw):
        raise cs.CrowdSecUnavailable('read timed out')

    monkeypatch.setattr(cs, '_cs_request_strict', fake)
    with pytest.raises(cs.CrowdSecUnavailable):
        cs.cs_decisions_stream()


def test_changing_credentials_forces_a_full_resync(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'http://lapi:8080')
    monkeypatch.setenv('CROWDSEC_API_KEY', 'first')
    paths = []

    def fake(method, path, **kw):
        paths.append(path)
        return _payload(new=[_dec(1, '1.1.1.1')])

    monkeypatch.setattr(cs, '_cs_request_strict', fake)
    cs.cs_decisions_stream()
    cs.cs_decisions_stream()
    assert 'startup=true' in paths[0] and 'startup=true' not in paths[1]

    monkeypatch.setenv('CROWDSEC_API_KEY', 'second')
    cs.cs_decisions_stream()
    assert 'startup=true' in paths[2]


def test_deleted_without_id_falls_back_to_value_match(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'http://lapi:8080')
    monkeypatch.setenv('CROWDSEC_API_KEY', 'k')
    state = {'n': 0}

    def fake(method, path, **kw):
        state['n'] += 1
        if state['n'] == 1:
            return _payload(new=[_dec(1, '9.9.9.9')])
        return _payload(deleted=[{'value': '9.9.9.9', 'type': 'ban'}])

    monkeypatch.setattr(cs, '_cs_request_strict', fake)
    cs.cs_decisions_stream()
    rows, _ = cs.cs_decisions_stream()
    assert rows == []
