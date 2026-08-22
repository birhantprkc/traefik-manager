import pytest


@pytest.fixture
def mon(monkeypatch, tmp_path):
    from core import monitor
    from core import notifications

    sent = []

    def _record(type_, msg, category=None, webhook=True):
        sent.append((type_, msg, category))
        return True

    monkeypatch.setattr(notifications, 'add_notification', _record)
    monkeypatch.setattr(monitor, '_state_path', lambda: str(tmp_path / 'monitor.json'))
    monkeypatch.setattr(monitor, '_lock_path', lambda: str(tmp_path / 'monitor.lock'))
    monkeypatch.setattr(monitor, '_checks', [])
    monitor._state.clear()
    yield monitor, sent
    monitor._state.clear()


def _alert(ip, scenario, events):
    return {'source': {'ip': ip, 'scope': 'Ip'}, 'scenario': scenario, 'events_count': events}


def test_a_window_of_alerts_collapses_into_one_message(monkeypatch):
    from core import crowdsec

    monkeypatch.setattr(crowdsec, 'poll_local_alerts', lambda since='10m': [
        _alert('1.2.3.4', 'crowdsecurity/http-probing', 30),
        _alert('1.2.3.4', 'crowdsecurity/http-probing', 12),
        _alert('5.6.7.8', 'crowdsecurity/ssh-bf', 9),
        _alert('9.9.9.9', 'crowdsecurity/http-crawl-non_statics', 4),
    ])

    raised = crowdsec.check_local_alerts('10m')
    assert len(raised) == 1, 'one message per window, got %r' % (raised,)

    type_, msg, category = raised[0]
    assert (type_, category) == ('warning', 'crowdsec')
    assert '3 sources' in msg and '3 scenarios' in msg
    assert '55 events' in msg, msg
    assert 'Worst: 1.2.3.4' in msg and 'http-probing' in msg
    assert 'ssh-bf' in msg, 'every scenario should be named, not only the worst'


def test_a_single_alert_reads_as_one_source_and_one_scenario(monkeypatch):
    from core import crowdsec

    monkeypatch.setattr(crowdsec, 'poll_local_alerts', lambda since='10m': [
        _alert('1.2.3.4', 'crowdsecurity/ssh-bf', 1),
    ])

    msg = crowdsec.check_local_alerts('10m')[0][1]
    assert msg.startswith('1.2.3.4 tripped 1 scenario'), msg
    assert '1 event' in msg and 'ssh-bf' in msg


def test_a_quiet_window_says_nothing(monkeypatch):
    from core import crowdsec

    monkeypatch.setattr(crowdsec, 'poll_local_alerts', lambda since='10m': [])
    assert crowdsec.check_local_alerts('10m') == []


def test_the_crowdsec_check_raises_one_notification_not_one_per_alert(mon, monkeypatch):
    from core import crowdsec

    monkeypatch.setattr(crowdsec, 'poll_local_alerts',
                        lambda since='10m': [_alert('10.0.0.%d' % i, 'crowdsecurity/ssh-bf', i)
                                             for i in range(1, 26)])
    monitor, sent = mon
    monitor.register('crowdsec', crowdsec.CS_ALERT_INTERVAL,
                     lambda: crowdsec.check_local_alerts(crowdsec.CS_ALERT_WINDOW))

    raised = monitor.run_checks_once(force=True)
    assert len(raised) == 1, raised
    assert len(sent) == 1, sent
    assert sent[0][2] == 'crowdsec'
    assert sent[0][1].startswith('25 sources tripped 1 scenario'), sent
    assert '325 events' in sent[0][1], sent


def test_compare_versions_matches_the_browser_check():
    from core import updates

    assert updates.compare_versions('1.13.0', '1.12.0') > 0
    assert updates.compare_versions('1.12.0', '1.12.0') == 0
    assert updates.compare_versions('1.9.1', '1.10.0') < 0
    assert updates.compare_versions('v3.4.1', '3.4') > 0
    assert updates.compare_versions('2.0', '2.0.0') == 0


def _versions(monkeypatch, manager='1.12.0', traefik='3.5.0', running='3.4.0'):
    from core import env
    from core import updates

    monkeypatch.setattr(env, 'APP_VERSION', '1.12.0')
    monkeypatch.setattr(updates, 'running_traefik_version', lambda: running)
    monkeypatch.setattr(updates, 'latest_release',
                        lambda repo: manager if repo == env.GITHUB_REPO else traefik)


def test_a_new_release_is_announced_once(monkeypatch):
    from core import updates

    _versions(monkeypatch, manager='1.13.0', traefik='3.5.0', running='3.4.0')
    seen = {}

    first = updates.check_updates(seen)
    msgs  = [m for _, m, _ in first]
    assert msgs == ['Traefik Manager v1.13.0 is available - update now',
                    'Traefik v3.5.0 is available - update now'], first
    assert {c for _, _, c in first} == {'update'}

    assert updates.check_updates(seen) == [], 'the same version alerted twice'
    assert updates.check_updates(seen) == [], 'the same version alerted on a third run'


def test_the_next_release_alerts_again(monkeypatch):
    from core import updates

    _versions(monkeypatch, manager='1.13.0', traefik='3.5.0', running='3.4.0')
    seen = {}
    assert len(updates.check_updates(seen)) == 2

    _versions(monkeypatch, manager='1.14.0', traefik='3.5.0', running='3.4.0')
    raised = updates.check_updates(seen)
    assert [m for _, m, _ in raised] == ['Traefik Manager v1.14.0 is available - update now'], raised


def test_an_older_or_equal_release_is_not_an_update(monkeypatch):
    from core import updates

    _versions(monkeypatch, manager='1.12.0', traefik='3.4.0', running='3.4.0')
    assert updates.check_updates({}) == []

    _versions(monkeypatch, manager='1.11.9', traefik='3.3.0', running='3.4.0')
    assert updates.check_updates({}) == []


def test_an_unreachable_source_says_nothing(monkeypatch):
    from core import updates

    _versions(monkeypatch, manager='', traefik='', running='')
    assert updates.check_updates({}) == []


def test_the_update_check_does_not_repeat_daily(mon, monkeypatch):
    from core import updates

    monitor, sent = mon
    _versions(monkeypatch, manager='1.13.0', traefik='3.4.0', running='3.4.0')
    monitor.register('updates', updates.UPDATE_INTERVAL, updates.check_updates)

    assert len(monitor.run_checks_once(force=True)) == 1
    assert monitor.run_checks_once(force=True) == [], 'the same version alerted the next day'

    monitor._state.clear()
    assert monitor.run_checks_once(force=True) == [], 'a restart re-alerted the same version'
    assert len(sent) == 1, sent
    assert sent[0] == ('info', 'Traefik Manager v1.13.0 is available - update now', 'update')
