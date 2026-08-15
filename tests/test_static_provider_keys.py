import json

import pytest


RAW = """\
providers:
  docker:
    endpoint: unix:///var/run/docker.sock
    network: web
    defaultRule: Host(`{{ .Name }}.example.com`)
    constraints: Label(`traefik.enable`,`true`)
    httpClientTimeout: 30
    allowEmptyServices: true
  file:
    directory: /etc/traefik/conf.d
    filename: /etc/traefik/extra.yml
    debugLogGeneratedTemplate: true
"""


def _post(client, payload):
    return client.post(
        '/api/static/section',
        data=json.dumps({
            'action': 'set',
            'section': 'providers',
            'name': 'providers',
            'current_raw': RAW,
            'data': payload,
        }),
        content_type='application/json',
        headers={'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'},
    )


@pytest.fixture
def saved(client):
    res = _post(client, {
        'docker': True,
        'dockerEndpoint': 'unix:///var/run/docker.sock',
        'dockerExposedByDefault': True,
        'dockerWatch': True,
        'file': True,
        'fileDirectory': '/etc/traefik/conf.d',
        'fileWatch': True,
    })
    assert res.status_code == 200, res.get_data(as_text=True)
    return res.get_json().get('raw', '')


@pytest.mark.parametrize('key', [
    'network',
    'defaultRule',
    'constraints',
    'httpClientTimeout',
    'allowEmptyServices',
])
def test_docker_keys_survive_a_provider_save(saved, key):
    assert key in saved, f'providers.docker.{key} was destroyed by saving the providers section'


@pytest.mark.parametrize('key', ['filename', 'debugLogGeneratedTemplate'])
def test_file_keys_survive_a_provider_save(saved, key):
    assert key in saved, f'providers.file.{key} was destroyed by saving the providers section'


def test_modelled_fields_still_apply(client):
    res = _post(client, {
        'docker': True,
        'dockerEndpoint': 'tcp://socket-proxy:2375',
        'dockerExposedByDefault': False,
        'dockerWatch': True,
        'file': True,
        'fileDirectory': '/srv/dynamic',
        'fileWatch': False,
    })
    assert res.status_code == 200
    raw = res.get_json().get('raw', '')
    assert 'tcp://socket-proxy:2375' in raw
    assert 'exposedByDefault: false' in raw
    assert '/srv/dynamic' in raw
    assert 'watch: false' in raw


def test_disabling_docker_still_removes_the_block(client):
    res = _post(client, {'docker': False, 'file': True, 'fileDirectory': '/etc/traefik/conf.d'})
    assert res.status_code == 200
    raw = res.get_json().get('raw', '')
    assert 'docker:' not in raw
    assert 'network: web' not in raw
