import core.updates as updates


def _reachable(monkeypatch, ok=True):
    monkeypatch.setattr(updates.monitor_mod, '_agent_reachable', lambda agent: ok)


def _only_traefik(tag):
    return lambda repo: tag if repo == updates.TRAEFIK_REPO else ''


def test_an_agent_running_an_old_traefik_is_announced(monkeypatch):
    monkeypatch.setattr(updates.monitor_mod, '_agents',
                        lambda: [{'id': 'a1', 'name': 'proxy', 'url': 'http://a1:8090'}])
    _reachable(monkeypatch)
    monkeypatch.setattr(updates.monitor_mod, '_agent_json',
                        lambda agent, path: {'Version': 'v3.0.0'})
    monkeypatch.setattr(updates, 'latest_release', _only_traefik('3.7.0'))
    monkeypatch.setattr(updates, 'running_traefik_version', lambda: '')
    seen = {}
    raised = updates.check_updates(seen)
    msgs = [m for _t, m, _c in raised]
    assert any('proxy' in m and '3.7.0' in m for m in msgs), msgs
    assert seen.get('traefik:a1') == '3.7.0'


def test_the_same_agent_release_is_not_announced_twice(monkeypatch):
    monkeypatch.setattr(updates.monitor_mod, '_agents',
                        lambda: [{'id': 'a1', 'name': 'proxy', 'url': 'http://a1:8090'}])
    _reachable(monkeypatch)
    monkeypatch.setattr(updates.monitor_mod, '_agent_json',
                        lambda agent, path: {'Version': 'v3.0.0'})
    monkeypatch.setattr(updates, 'latest_release', _only_traefik('3.7.0'))
    monkeypatch.setattr(updates, 'running_traefik_version', lambda: '')
    seen = {}
    assert updates.check_updates(seen)
    assert updates.check_updates(seen) == [], 'a second run must stay silent'


def test_an_up_to_date_agent_is_silent(monkeypatch):
    monkeypatch.setattr(updates.monitor_mod, '_agents',
                        lambda: [{'id': 'a1', 'name': 'proxy', 'url': 'http://a1:8090'}])
    _reachable(monkeypatch)
    monkeypatch.setattr(updates.monitor_mod, '_agent_json',
                        lambda agent, path: {'Version': 'v3.7.0'})
    monkeypatch.setattr(updates, 'latest_release', _only_traefik('3.7.0'))
    monkeypatch.setattr(updates, 'running_traefik_version', lambda: '')
    assert updates.check_updates({}) == []


def test_an_unreachable_agent_is_skipped_not_raised(monkeypatch):
    def boom(agent, path): raise RuntimeError('agent down')
    monkeypatch.setattr(updates.monitor_mod, '_agents',
                        lambda: [{'id': 'a1', 'name': 'proxy', 'url': 'http://a1:8090'}])
    _reachable(monkeypatch)
    monkeypatch.setattr(updates.monitor_mod, '_agent_json', boom)
    monkeypatch.setattr(updates, 'latest_release', _only_traefik('3.7.0'))
    monkeypatch.setattr(updates, 'running_traefik_version', lambda: '')
    assert updates.check_updates({}) == []


def test_github_is_asked_once_per_repo_per_run(monkeypatch):
    calls = []
    monkeypatch.setattr(updates.monitor_mod, '_agents', lambda: [
        {'id': 'a1', 'name': 'one', 'url': 'http://a1:8090'},
        {'id': 'a2', 'name': 'two', 'url': 'http://a2:8090'},
    ])
    _reachable(monkeypatch)
    monkeypatch.setattr(updates.monitor_mod, '_agent_json',
                        lambda agent, path: {'Version': 'v3.0.0'})
    monkeypatch.setattr(updates, 'latest_release',
                        lambda repo: (calls.append(repo), '3.7.0' if repo == updates.TRAEFIK_REPO else '')[1])
    monkeypatch.setattr(updates, 'running_traefik_version', lambda: '3.0.0')
    updates.check_updates({})
    assert calls.count(updates.TRAEFIK_REPO) == 1, f'GitHub asked {calls.count(updates.TRAEFIK_REPO)}x'


def test_an_unreachable_agent_is_never_asked_for_its_version(monkeypatch):
    asked = []
    monkeypatch.setattr(updates.monitor_mod, '_agents',
                        lambda: [{'id': 'a1', 'name': 'proxy', 'url': 'http://a1:8090'}])
    monkeypatch.setattr(updates.monitor_mod, '_agent_reachable', lambda agent: False)
    monkeypatch.setattr(updates.monitor_mod, '_agent_json',
                        lambda agent, path: (asked.append(path), {'Version': 'v3.0.0'})[1])
    monkeypatch.setattr(updates, 'latest_release', _only_traefik('3.7.0'))
    monkeypatch.setattr(updates, 'running_traefik_version', lambda: '')
    assert updates.check_updates({}) == []
    assert asked == [], f'an unreachable agent was still probed: {asked}'
