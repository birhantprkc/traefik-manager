import os

import core.agents_store as store
import core.env as env
import core.git as git_mod
import core.settings as settings_mod


def _seed(agent_id='a1'):
    store.save_agents_file([{'id': agent_id, 'name': 'alpha',
                             'url': 'http://a1:8090', 'api_key': 'k1'}])
    repo = git_mod._git_agent_repo_dir(agent_id)
    os.makedirs(os.path.join(repo, '.git'), exist_ok=True)
    with open(os.path.join(repo, '.git', 'credentials'), 'w') as fh:
        fh.write('https://user:token@github.com\n')
    return repo


def _settings_with(**over):
    s = settings_mod.load_settings()
    base = dict(domains=s['domains'], cert_resolver=s['cert_resolver'],
                traefik_api_url=s['traefik_api_url'], auth_enabled=s['auth_enabled'],
                password_hash=s['password_hash'], visible_tabs=s['visible_tabs'])
    base.update(over)
    settings_mod.save_settings(**base)


def _delete(client, agent_id):
    return client.delete('/api/agents/' + agent_id,
                         headers={'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'})


def test_deleting_an_agent_removes_its_git_clone(client):
    repo = _seed()
    assert os.path.isdir(repo)
    assert _delete(client, 'a1').status_code < 400
    assert not os.path.exists(repo), 'a clone of the config repo with credential state was left behind'


def test_another_agents_clone_is_untouched(client):
    _seed('a1')
    other = git_mod._git_agent_repo_dir('a2')
    os.makedirs(other, exist_ok=True)
    _delete(client, 'a1')
    assert os.path.isdir(other)


def test_deleting_an_unknown_agent_removes_nothing(client):
    repo = _seed('a1')
    assert _delete(client, 'nope').status_code < 400
    assert os.path.isdir(repo), 'a bogus id must not delete anything'
    assert len(store.load_agents()) == 1


def test_the_host_git_repo_is_never_touched(client):
    _seed('a1')
    host_repo = git_mod._git_repo_dir()
    os.makedirs(host_repo, exist_ok=True)
    _delete(client, 'a1')
    assert os.path.isdir(host_repo), 'only git-agent-* directories may be removed'


def test_agent_scoped_settings_are_forgotten(client):
    _seed('a1')
    _settings_with(
        disabled_routes={'agent_a1::r1': {'protocol': 'http'}, 'kept': {'protocol': 'http'}},
        managed_middlewares={'agent_a1::tp::x-transport': {'kind': 'route-transport'},
                             'tp::host-transport': {'kind': 'route-transport'}})
    _delete(client, 'a1')
    s = settings_mod.load_settings()
    assert 'agent_a1::r1' not in s['disabled_routes']
    assert 'kept' in s['disabled_routes'], 'host entries must survive'
    assert 'agent_a1::tp::x-transport' not in s['managed_middlewares']
    assert 'tp::host-transport' in s['managed_middlewares']


def test_a_missing_clone_is_not_an_error(client):
    store.save_agents_file([{'id': 'a9', 'name': 'nine', 'url': 'http://a9:8090', 'api_key': 'k'}])
    assert _delete(client, 'a9').status_code < 400
    assert store.load_agents() == []


def test_an_orphan_clone_for_an_unregistered_id_is_left_alone(client):
    _seed('a1')
    orphan = git_mod._git_agent_repo_dir('ghost')
    os.makedirs(orphan, exist_ok=True)
    _settings_with(disabled_routes={'agent_ghost::r1': {'protocol': 'http'}})
    assert _delete(client, 'ghost').status_code < 400
    assert os.path.isdir(orphan), 'an id that is not a registered agent must not delete anything'
    assert 'agent_ghost::r1' in settings_mod.load_settings()['disabled_routes']


def test_the_helper_refuses_a_path_outside_the_agent_clone_pattern(client, monkeypatch):
    victim = os.path.join(env.BACKUP_DIR, 'not-an-agent-dir')
    os.makedirs(victim, exist_ok=True)
    import app as tm
    monkeypatch.setattr(tm, '_git_agent_repo_dir', lambda _id: victim)
    assert tm._remove_agent_git_clone('a1') is False
    assert os.path.isdir(victim), 'only git-agent-* directories may be removed'


def test_the_helper_refuses_a_path_outside_backup_dir(client, monkeypatch, tmp_path):
    outside = str(tmp_path / 'git-agent-elsewhere')
    os.makedirs(outside, exist_ok=True)
    import app as tm
    monkeypatch.setattr(tm, '_git_agent_repo_dir', lambda _id: outside)
    assert tm._remove_agent_git_clone('a1') is False
    assert os.path.isdir(outside), 'nothing outside BACKUP_DIR may be removed'
