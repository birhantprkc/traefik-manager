import os

import pytest

from core import env
from core import monitor


@pytest.fixture
def storage(tmp_path, monkeypatch):
    cfg = tmp_path / 'config'
    cfg.mkdir()
    monkeypatch.setattr(env, 'CONFIG_DIR', str(cfg))
    monkeypatch.setattr(env, 'BACKUP_DIR', str(tmp_path / 'backups'))
    monkeypatch.setattr(env, 'CONFIG_PATHS', [str(cfg / 'dynamic.yml')])
    monkeypatch.setattr(env, 'STATIC_CONFIG_DIRS', [])
    monkeypatch.setattr(monitor, '_persist_ok', True)
    monitor._memory_state.clear()
    monitor._state.clear()
    return cfg


def test_a_healthy_setup_reports_nothing(storage):
    assert env.unwritable_storage() == []


def test_an_unwritable_directory_is_reported(storage):
    os.chmod(storage, 0o500)
    try:
        bad = env.unwritable_storage()
    finally:
        os.chmod(storage, 0o700)
    assert [label for label, _p, _e in bad] == ['Configuration']
    assert str(storage) in bad[0][1]
    assert bad[0][2]


def test_the_probe_leaves_nothing_behind(storage):
    env.unwritable_storage()
    assert [p for p in os.listdir(storage) if 'probe' in p] == []


def test_a_missing_backup_directory_is_created_not_reported(storage, tmp_path):
    assert not (tmp_path / 'backups').exists()
    assert env.unwritable_storage() == []
    assert (tmp_path / 'backups').is_dir()


def test_a_backup_directory_that_cannot_be_created_is_reported(storage, tmp_path, monkeypatch):
    blocked = tmp_path / 'blocked'
    blocked.mkdir()
    monkeypatch.setattr(env, 'BACKUP_DIR', str(blocked / 'backups'))
    os.chmod(blocked, 0o500)
    try:
        bad = env.unwritable_storage()
    finally:
        os.chmod(blocked, 0o700)
    assert any(label == 'Backups' for label, _p, _e in bad)
    assert any('cannot be created' in err for _l, _p, err in bad)


def test_the_same_directory_is_only_probed_once(storage):
    labels = [label for label, _p in env.storage_targets()]
    paths = [p for _l, p in env.storage_targets()]
    assert len(paths) == len(set(paths)), 'a shared directory must not be probed twice'
    assert 'Configuration' in labels


def _run(sent):
    monitor.run_checks_once(force=True)
    return len(sent)


@pytest.fixture
def alerts(storage, monkeypatch):
    sent = []
    monkeypatch.setattr(monitor, '_checks', [('storage', 300, monitor._check_storage)])
    monkeypatch.setattr(monitor, '_notify', lambda t, m, c: sent.append((t, c, m)))
    return sent


def test_no_alert_while_storage_is_healthy(alerts):
    _run(alerts)
    _run(alerts)
    assert alerts == []


def test_one_alert_when_storage_breaks_not_one_per_cycle(alerts, storage):
    os.chmod(storage, 0o500)
    try:
        _run(alerts)
        _run(alerts)
        _run(alerts)
    finally:
        os.chmod(storage, 0o700)
    assert len(alerts) == 1, 'the alert must not repeat every cycle'
    kind, category, message = alerts[0]
    assert kind == 'error'
    assert category in ('config',)
    assert 'not writable' in message


def test_recovery_is_announced(alerts, storage):
    os.chmod(storage, 0o500)
    try:
        _run(alerts)
    finally:
        os.chmod(storage, 0o700)
    _run(alerts)
    assert len(alerts) == 2
    assert alerts[1][0] == 'success'
    assert 'writable again' in alerts[1][2]


def test_the_alert_category_is_one_channels_already_know(alerts, storage):
    from core import settings
    os.chmod(storage, 0o500)
    try:
        _run(alerts)
    finally:
        os.chmod(storage, 0o700)
    assert alerts[0][1] in settings.CHANNEL_CATEGORIES


def test_memory_wins_once_a_save_has_failed(storage, monkeypatch):
    monitor._state.clear()
    monitor._state.update({'due': {'x': 5.0}})
    monitor._write_state()
    assert monitor._persist_ok

    def boom(*a, **kw):
        raise OSError('read-only file system')

    monkeypatch.setattr(monitor.cfg_mod, '_replace_or_copy', boom)
    monitor._state['due']['x'] = 99.0
    monitor._write_state()
    assert monitor._persist_ok is False
    assert monitor._read_state()['due']['x'] == 99.0, \
        'a readable but stale file must not overwrite what is in memory'


def test_a_recovered_save_trusts_the_file_again(storage, monkeypatch):
    monkeypatch.setattr(monitor, '_persist_ok', False)
    monitor._state.clear()
    monitor._state.update({'due': {'x': 1.0}})
    monitor._write_state()
    assert monitor._persist_ok is True


def test_the_status_endpoint_is_empty_when_healthy(client):
    r = client.get('/api/storage/status')
    assert r.status_code == 200
    assert r.get_json() == {'problems': []}


def test_the_status_endpoint_reports_a_broken_directory(client, monkeypatch):
    import app as tm
    monkeypatch.setattr(env, 'unwritable_storage',
                        lambda: [('Configuration', '/app/config', 'read-only file system')])
    tm._storage_probe_cache['at'] = 0
    try:
        r = client.get('/api/storage/status')
        problems = r.get_json()['problems']
    finally:
        tm._storage_probe_cache['at'] = 0
    assert problems == [{'label': 'Configuration', 'path': '/app/config',
                         'error': 'read-only file system'}]


def test_the_status_endpoint_requires_a_session(anon_client):
    r = anon_client.get('/api/storage/status')
    assert r.status_code != 200


def test_the_probe_is_cached_so_open_tabs_do_not_hammer_the_disk(client, monkeypatch):
    import app as tm
    calls = []
    monkeypatch.setattr(env, 'unwritable_storage', lambda: calls.append(1) or [])
    tm._storage_probe_cache['at'] = 0
    try:
        c = client
        for _ in range(5):
            c.get('/api/storage/status')
    finally:
        tm._storage_probe_cache['at'] = 0
    assert len(calls) == 1


def test_the_banner_element_sits_outside_any_tab():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, 'templates', 'index.html'), encoding='utf-8') as fh:
        html = fh.read()
    assert html.count('id="storageBanner"') == 1
    before = html.split('id="storageBanner"')[0]
    assert '<main' in before, 'the banner must be inside main so it shows on every tab'
    assert "include 'tabs/" not in before, 'the banner must not live inside one tab'


def test_the_banner_is_refreshed_on_load():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, 'static', 'js', 'init.js'), encoding='utf-8') as fh:
        js = fh.read()
    assert 'refreshStorageBanner()' in js
    assert 'setInterval(refreshStorageBanner' in js
