import json
import os
import re

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


TRAEFIK_PROVIDER_KEYS = {
    'docker', 'swarm', 'file', 'http', 'kubernetesCRD', 'kubernetesIngress',
    'kubernetesGateway', 'nomad', 'ecs', 'consulCatalog', 'consul', 'redis',
    'etcd', 'zooKeeper', 'plugin',
}
STATIC_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'static', 'js', 'static-config.js')


def _static_js():
    with open(STATIC_JS, encoding='utf-8') as fh:
        return fh.read()


def _dropdown_values():
    src = _static_js()
    block = src[src.index('id="sfProviderType"'):]
    block = block[:block.index('</select>')]
    return [v for v in re.findall(r'<option value="([^"]*)"', block) if v]


def _template_keys():
    src = _static_js()
    block = src[src.index('const PROVIDER_TEMPLATES = {'):]
    block = block[:block.index('\n};')]
    return re.findall(r'^\s{4}(\w+):', block, re.M)


def test_every_provider_option_is_a_key_traefik_understands():
    for value in _dropdown_values():
        assert value in TRAEFIK_PROVIDER_KEYS, \
            f'{value!r} is not a Traefik static provider key, so the section it writes is ignored'


def test_every_template_is_a_key_traefik_understands():
    for key in _template_keys():
        assert key in TRAEFIK_PROVIDER_KEYS, f'{key!r} is not a Traefik static provider key'


def test_every_option_has_a_template():
    templates = set(_template_keys())
    for value in _dropdown_values():
        assert value in templates, f'{value} is offered with no template behind it'


def test_the_crd_provider_is_offered():
    assert 'kubernetesCRD' in _dropdown_values()
