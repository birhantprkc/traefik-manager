import core.monitor as monitor


class _Resp:
    def __init__(self, code):
        self.status_code = code

    def json(self):
        return {}


def _agents(monkeypatch, agents):
    monkeypatch.setattr(monitor, '_agents', lambda: agents)


AGENT = {'id': 'a1', 'name': 'proxy', 'url': 'http://a1:8090', 'api_key': 'k'}


def _reset():
    monitor._cycle_up.clear()
    monitor._cycle_auth.clear()
    monitor._state.clear()


def test_a_refused_key_is_reported_once_not_as_three_failures(monkeypatch):
    _reset()
    _agents(monkeypatch, [AGENT])
    monkeypatch.setattr(monitor, '_agent_up', lambda a: True)
    monkeypatch.setattr(monitor.agents_http_mod, '_agent_request',
                        lambda *a, **k: _Resp(401))
    raised = monitor._check_agents()
    assert len(raised) == 1, raised
    kind, msg, cat = raised[0]
    assert kind == 'error' and cat == 'agent'
    assert 'rejected the API key' in msg
    assert 'unreachable' not in msg


def test_the_dependent_checks_skip_an_agent_whose_key_is_refused(monkeypatch):
    _reset()
    _agents(monkeypatch, [AGENT])
    monkeypatch.setattr(monitor, '_agent_up', lambda a: True)
    monkeypatch.setattr(monitor.agents_http_mod, '_agent_request',
                        lambda *a, **k: _Resp(401))
    assert monitor._agent_usable(AGENT) is False, \
        'Traefik, CrowdSec and cert checks all gate on this'


def test_a_working_agent_is_still_usable(monkeypatch):
    _reset()
    monkeypatch.setattr(monitor, '_agent_up', lambda a: True)
    monkeypatch.setattr(monitor.agents_http_mod, '_agent_request',
                        lambda *a, **k: _Resp(200))
    assert monitor._agent_usable(AGENT) is True


def test_an_unreachable_agent_still_says_unreachable(monkeypatch):
    _reset()
    _agents(monkeypatch, [AGENT])
    monkeypatch.setattr(monitor, '_agent_up', lambda a: False)
    raised = monitor._check_agents()
    assert len(raised) == 1
    assert 'unreachable' in raised[0][1]


def test_the_auth_probe_runs_once_per_cycle(monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr(monitor, '_agent_up', lambda a: True)

    def probe(*a, **k):
        calls.append(1)
        return _Resp(200)

    monkeypatch.setattr(monitor.agents_http_mod, '_agent_request', probe)
    for _ in range(4):
        monitor._agent_usable(AGENT)
    assert len(calls) == 1, 'the probe must be cached like the health check'


def test_a_transport_error_is_not_treated_as_a_bad_key(monkeypatch):
    _reset()
    monkeypatch.setattr(monitor, '_agent_up', lambda a: True)

    def boom(*a, **k):
        raise OSError('connection reset')

    monkeypatch.setattr(monitor.agents_http_mod, '_agent_request', boom)
    assert monitor._agent_key_accepted(AGENT) is True, \
        'only a 401 means the key is wrong'


def test_the_old_boolean_state_upgrades_without_a_false_alert(monkeypatch):
    _reset()
    _agents(monkeypatch, [AGENT])
    monkeypatch.setattr(monitor, '_agent_up', lambda a: True)
    monkeypatch.setattr(monitor.agents_http_mod, '_agent_request',
                        lambda *a, **k: _Resp(200))
    monitor._section('agents')['a1'] = True
    assert monitor._check_agents() == [], 'an upgrade must not announce a change that did not happen'
