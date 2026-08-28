import os
import subprocess
import sys
import textwrap
import time

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RUNNER = textwrap.dedent("""
    import os
    from core import monitor
    monitor._lock_path = lambda: os.environ['TM_MONITOR_LOCK']
    monitor.run_checks_once = lambda force=False: []
    print(monitor.start())
""")


@pytest.fixture
def mon(monkeypatch, tmp_path):
    from core import certs as certs_mod
    from core import geoip as geoip_mod
    from core import monitor
    from core import notifications
    from core import settings as settings_mod
    from core import traefik as traefik_mod

    sent = []

    def _record(type_, msg, category=None, webhook=True):
        sent.append((type_, msg, category))
        return True

    monkeypatch.setattr(notifications, 'add_notification', _record)
    monkeypatch.setattr(monitor, '_state_path', lambda: str(tmp_path / 'monitor.json'))
    monkeypatch.setattr(monitor, '_lock_path', lambda: str(tmp_path / 'monitor.lock'))
    monkeypatch.setattr(monitor, '_checks', list(monitor._checks))
    monkeypatch.setattr(settings_mod, 'get_acme_json_paths', lambda: [])
    monkeypatch.setattr(certs_mod, '_certs_from_tls_configs', lambda: [])
    monkeypatch.setattr(traefik_mod, 'traefik_api_get', lambda path: {'ok': True})
    monkeypatch.setattr(geoip_mod, '_geoip_enabled', lambda: False)
    monkeypatch.setattr(monitor, '_agents', lambda: [])
    monitor._state.clear()
    yield monitor, sent
    monitor._state.clear()


def _iso(base, days):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(base + days * 86400))


def _only(sent, category):
    return [s for s in sent if s[2] == category]


def test_an_expiring_cert_alerts_once_not_every_cycle(mon, monkeypatch):
    monitor, sent = mon
    from core import certs as certs_mod

    base = time.time()
    monkeypatch.setattr(certs_mod, '_certs_from_tls_configs', lambda: [
        {'resolver': 'file', 'main': 'shop.example.com', 'not_after': _iso(base, 10)},
    ])
    monkeypatch.setattr(monitor, '_now', lambda: base)

    first = monitor.run_checks_once(force=True)
    assert _only(first, 'certs'), 'a cert 10 days from expiry raised nothing'
    assert len(_only(first, 'certs')) == 1
    assert _only(first, 'certs')[0][0] == 'warning'
    assert 'shop.example.com' in _only(first, 'certs')[0][1]

    second = monitor.run_checks_once(force=True)
    assert _only(second, 'certs') == [], 'the same cert alerted twice'
    assert len(_only(sent, 'certs')) == 1, sent


def test_each_expiry_threshold_fires_once(mon, monkeypatch):
    monitor, sent = mon
    from core import certs as certs_mod

    base = time.time()
    monkeypatch.setattr(certs_mod, '_certs_from_tls_configs', lambda: [
        {'resolver': 'le', 'main': 'api.example.com', 'not_after': _iso(base, 10)},
    ])

    for offset, expected in ((0, 1), (0, 0), (8, 1), (8, 0), (11, 1), (11, 0)):
        monkeypatch.setattr(monitor, '_now', lambda o=offset: base + o * 86400)
        raised = _only(monitor.run_checks_once(force=True), 'certs')
        assert len(raised) == expected, 'day %d raised %r' % (offset, raised)

    kinds = [s[0] for s in _only(sent, 'certs')]
    assert kinds == ['warning', 'warning', 'error'], sent


def test_a_renewed_cert_arms_the_thresholds_again(mon, monkeypatch):
    monitor, sent = mon
    from core import certs as certs_mod

    base  = time.time()
    state = {'not_after': _iso(base, 2)}
    monkeypatch.setattr(certs_mod, '_certs_from_tls_configs', lambda: [
        {'resolver': 'le', 'main': 'api.example.com', 'not_after': state['not_after']},
    ])
    monkeypatch.setattr(monitor, '_now', lambda: base)

    assert len(_only(monitor.run_checks_once(force=True), 'certs')) == 1
    assert _only(monitor.run_checks_once(force=True), 'certs') == []

    state['not_after'] = _iso(base, 90)
    assert _only(monitor.run_checks_once(force=True), 'certs') == [], 'a fresh cert alerted'

    state['not_after'] = _iso(base, 1)
    assert len(_only(monitor.run_checks_once(force=True), 'certs')) == 1, 'renewal did not rearm'


def test_traefik_down_then_up_raises_exactly_two(mon, monkeypatch):
    monitor, sent = mon
    from core import traefik as traefik_mod

    monkeypatch.setattr(traefik_mod, 'traefik_api_get', lambda path: None)
    monitor.run_checks_once(force=True)
    monitor.run_checks_once(force=True)
    monitor.run_checks_once(force=True)

    monkeypatch.setattr(traefik_mod, 'traefik_api_get', lambda path: {'ok': True})
    monitor.run_checks_once(force=True)
    monitor.run_checks_once(force=True)

    raised = _only(sent, 'traefik')
    assert len(raised) == 2, raised
    assert raised[0][0] == 'error'
    assert raised[1][0] == 'success'


def test_traefik_up_from_the_start_is_silent(mon):
    monitor, sent = mon
    monitor.run_checks_once(force=True)
    monitor.run_checks_once(force=True)
    assert _only(sent, 'traefik') == [], sent


def test_agent_down_and_back_up_is_edge_triggered(mon, monkeypatch):
    monitor, sent = mon

    reachable = {'vps1': False, 'vps2': True}

    class _Resp:
        def __init__(self, code):
            self.status_code = code

    def _get(url, **kwargs):
        for agent_id, ok in reachable.items():
            if agent_id in url:
                return _Resp(200 if ok else 502)
        raise AssertionError('unexpected url %r' % url)

    monkeypatch.setattr(monitor.requests, 'get', _get)
    monkeypatch.setattr(monitor, '_agents', lambda: [
        {'id': 'vps1', 'name': 'VPS One', 'url': 'http://vps1.invalid:8080'},
        {'id': 'vps2', 'name': 'VPS Two', 'url': 'http://vps2.invalid:8080'},
    ])

    monitor.run_checks_once(force=True)
    monitor.run_checks_once(force=True)
    assert [s[1] for s in _only(sent, 'agent')] == ['Agent VPS One is unreachable'], sent

    reachable['vps1'] = True
    monitor.run_checks_once(force=True)
    monitor.run_checks_once(force=True)
    raised = _only(sent, 'agent')
    assert len(raised) == 2, raised
    assert raised[1] == ('success', 'Agent VPS One is back online', 'agent')


def test_a_check_is_skipped_until_its_interval_elapses(mon):
    monitor, sent = mon
    calls = []
    monitor.register('crowdsec', 3600, lambda: calls.append(1) or [])

    monitor.run_checks_once(force=True)
    monitor.run_checks_once()
    assert len(calls) == 1, 'the check ran again before its interval elapsed'


def test_a_registered_check_can_raise_notifications(mon):
    monitor, sent = mon
    monitor.register('crowdsec', 60, lambda: [('warning', 'CrowdSec decisions spiked', 'crowdsec')])

    raised = monitor.run_checks_once(force=True)
    assert ('warning', 'CrowdSec decisions spiked', 'crowdsec') in raised
    assert ('warning', 'CrowdSec decisions spiked', 'crowdsec') in sent


def test_registering_the_same_name_twice_replaces_it(mon):
    monitor, sent = mon
    monitor.register('crowdsec', 60, lambda: [('info', 'first', 'crowdsec')])
    monitor.register('crowdsec', 60, lambda: [('info', 'second', 'crowdsec')])

    msgs = [s[1] for s in monitor.run_checks_once(force=True) if s[2] == 'crowdsec']
    assert msgs == ['second'], msgs


def test_one_exploding_check_does_not_stop_the_others(mon):
    monitor, sent = mon

    def _boom():
        raise RuntimeError('lapi is down')

    monitor.register('crowdsec', 60, _boom)
    monitor.register('other', 60, lambda: [('info', 'still running', 'security')])

    raised = monitor.run_checks_once(force=True)
    assert ('info', 'still running', 'security') in raised


def test_state_survives_a_restart(mon, monkeypatch):
    monitor, sent = mon
    from core import certs as certs_mod

    base = time.time()
    monkeypatch.setattr(certs_mod, '_certs_from_tls_configs', lambda: [
        {'resolver': 'le', 'main': 'api.example.com', 'not_after': _iso(base, 5)},
    ])
    monkeypatch.setattr(monitor, '_now', lambda: base)

    assert len(_only(monitor.run_checks_once(force=True), 'certs')) == 1
    monitor._state.clear()
    assert _only(monitor.run_checks_once(force=True), 'certs') == [], 'state was not persisted'


def test_only_one_process_becomes_the_runner(monkeypatch, tmp_path):
    from core import monitor

    lock = str(tmp_path / 'monitor.lock')
    monkeypatch.setattr(monitor, 'run_checks_once', lambda force=False: [])
    monkeypatch.setattr(monitor, '_lock_path', lambda: lock)

    def _other_process():
        env = dict(os.environ)
        env['PYTHONPATH'] = REPO
        env['TM_MONITOR_LOCK'] = lock
        proc = subprocess.run([sys.executable, '-c', RUNNER], env=env, cwd=REPO,
                              capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, proc.stderr
        return proc.stdout.strip().splitlines()[-1]

    monitor.stop()
    start = getattr(monitor, 'real_start', monitor.start)
    assert start() is True
    try:
        assert start() is True, 'start is not idempotent inside one process'
        assert _other_process() == 'False', 'a second worker also became the runner'
    finally:
        monitor.stop()
    assert _other_process() == 'True', 'the lock was not released for a later worker'
