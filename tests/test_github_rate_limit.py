import os

import pytest

import core.updates as updates
import core.monitor as monitor


@pytest.fixture(autouse=True)
def _clear():
    updates._release_cache.clear()
    monitor._memory_state.clear()
    yield
    updates._release_cache.clear()
    monitor._memory_state.clear()


class _Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _Github:
    def __init__(self, monkeypatch):
        self.hits = []
        self.reply = _Resp(200, {'tag_name': 'v1.0.0'})
        monkeypatch.setattr(updates.requests, 'get', self._get)

    def _get(self, url, **kw):
        self.hits.append(url)
        return self.reply

    def raise_on_call(self, monkeypatch):
        def boom(url, **kw):
            self.hits.append(url)
            raise OSError('no route to host')
        monkeypatch.setattr(updates.requests, 'get', boom)


def _expire(repo, ttl=None):
    _stamp, info, cached_ttl = updates._release_cache[repo]
    updates._release_cache[repo] = (0, info, ttl if ttl is not None else cached_ttl)


def test_latest_release_does_not_call_github_every_time(monkeypatch):
    gh = _Github(monkeypatch)
    for _ in range(5):
        assert updates.latest_release('owner/repo') == '1.0.0'
    assert len(gh.hits) == 1, 'the update check must reuse the cached release'


def test_latest_release_and_release_info_share_one_lookup(monkeypatch):
    gh = _Github(monkeypatch)
    updates.latest_release('owner/repo')
    updates.release_info('owner/repo')
    assert len(gh.hits) == 1


def test_a_rate_limited_refresh_stops_calling_github(monkeypatch):
    gh = _Github(monkeypatch)
    updates.release_info('owner/repo')
    _expire('owner/repo')
    gh.reply = _Resp(403)
    gh.hits.clear()
    for _ in range(5):
        updates.release_info('owner/repo')
    assert len(gh.hits) == 1, 'a rate limited answer must back off, not retry every call'


def test_a_rate_limited_refresh_keeps_the_last_known_tag(monkeypatch):
    gh = _Github(monkeypatch)
    updates.release_info('owner/repo')
    _expire('owner/repo')
    gh.reply = _Resp(403)
    out = updates.release_info('owner/repo')
    assert out['tag'] == '1.0.0'
    assert 'rate limited' in out['error']


def test_a_first_ever_failure_is_still_cached(monkeypatch):
    gh = _Github(monkeypatch)
    gh.reply = _Resp(403)
    for _ in range(5):
        updates.release_info('owner/repo')
    assert len(gh.hits) == 1


def test_a_rate_limit_backs_off_longer_than_a_network_error(monkeypatch):
    gh = _Github(monkeypatch)
    gh.reply = _Resp(403)
    updates.release_info('a/b')
    limited = updates._release_cache['a/b'][2]
    gh.raise_on_call(monkeypatch)
    updates.release_info('c/d')
    broken = updates._release_cache['c/d'][2]
    assert limited > broken, 'a rate limit must wait longer than a transient failure'


def test_check_updates_is_one_lookup_per_repo_however_often_it_runs(monkeypatch):
    gh = _Github(monkeypatch)
    gh.reply = _Resp(200, {'tag_name': 'v9.9.9'})
    monkeypatch.setattr(updates, 'running_traefik_version', lambda: '3.0.0')
    monkeypatch.setattr(updates.monitor_mod, '_agents', lambda: [])
    for _ in range(6):
        updates.check_updates(seen={})
    assert len(gh.hits) == 2, 'one lookup per repo, reused across runs'


def test_the_interval_holds_when_state_cannot_be_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor.env, 'CONFIG_DIR', str(tmp_path))
    calls = []
    monkeypatch.setattr(monitor, '_checks', [('updates', 86400, lambda: calls.append(1) or [])])
    os.chmod(tmp_path, 0o500)
    try:
        for _ in range(4):
            monitor.run_checks_once()
    finally:
        os.chmod(tmp_path, 0o700)
    assert len(calls) == 1, 'a failed save must not turn a daily check into every cycle'


def test_state_falls_back_to_memory_when_the_file_is_gone(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor.env, 'CONFIG_DIR', str(tmp_path))
    monitor._state.clear()
    monitor._state.update({'due': {'updates': 1234.0}})
    monitor._write_state()
    os.remove(monitor._state_path())
    assert monitor._read_state() == {'due': {'updates': 1234.0}}


def test_the_file_still_wins_over_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor.env, 'CONFIG_DIR', str(tmp_path))
    monitor._memory_state.clear()
    monitor._memory_state.update({'due': {'updates': 1.0}})
    with open(monitor._state_path(), 'w') as fh:
        fh.write('{"due": {"updates": 777.0}}')
    assert monitor._read_state()['due']['updates'] == 777.0


def test_memory_state_is_a_copy_not_a_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(monitor.env, 'CONFIG_DIR', str(tmp_path))
    monitor._state.clear()
    monitor._state.update({'due': {'updates': 1.0}})
    monitor._write_state()
    monitor._state['due']['updates'] = 999.0
    assert monitor._memory_state['due']['updates'] == 1.0
