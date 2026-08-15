import os

from core import env


def _mk_backup(name, content):
    os.makedirs(env.BACKUP_DIR, exist_ok=True)
    p = os.path.join(env.BACKUP_DIR, name)
    with open(p, 'w') as f:
        f.write(content)
    return p


def test_static_backup_restores_to_traefik_yml_not_dynamic(client, monkeypatch):
    static_path = os.environ.get('STATIC_CONFIG_PATH', '')
    assert static_path, 'test env must define STATIC_CONFIG_PATH'

    dynamic_before = open(env.CONFIG_PATH).read()
    _mk_backup(os.path.basename(static_path) + '.20260101_000000.bak',
               'entryPoints:\n  web:\n    address: ":80"\n')

    r = client.post('/api/restore/' + os.path.basename(static_path) + '.20260101_000000.bak',
                    headers={'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'})
    assert r.status_code == 200, r.data

    dynamic_after = open(env.CONFIG_PATH).read()
    assert dynamic_after == dynamic_before, (
        'restoring a static backup overwrote the dynamic config file')

    static_after = open(static_path).read()
    assert 'entryPoints' in static_after, (
        'static backup was not restored into traefik.yml')


def test_dynamic_backup_still_restores_to_its_own_file(client):
    name = os.path.basename(env.CONFIG_PATH) + '.20260101_000000.bak'
    _mk_backup(name, 'http:\n  routers:\n    marker: {}\n')

    r = client.post('/api/restore/' + name,
                    headers={'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'})
    assert r.status_code == 200, r.data
    assert 'marker' in open(env.CONFIG_PATH).read()
