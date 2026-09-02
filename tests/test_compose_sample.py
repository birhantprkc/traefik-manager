import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def test_the_static_config_mount_is_writable():
    line = [ln for ln in _read('docker-compose.yml').splitlines() if 'traefik.yml:/app/traefik.yml' in ln]
    assert line, 'the static config mount example moved'
    assert not line[0].rstrip().endswith(':ro'), \
        'docs/docker.md says to mount it read-write, or saving the static config fails'


def test_the_read_only_mounts_stay_read_only():
    src = _read('docker-compose.yml')
    for path in ('acme.json', 'access.log'):
        line = [ln for ln in src.splitlines() if path in ln and '/app/' in ln]
        assert line, f'the {path} mount example moved'
        assert line[0].rstrip().endswith(':ro'), f'{path} is only ever read'
