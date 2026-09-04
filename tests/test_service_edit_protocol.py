import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, 'static', 'js', 'services.js')


def _fn(name):
    with open(JS, encoding='utf-8') as fh:
        src = fh.read()
    m = re.search(r'(function ' + name + r'\(.*?\n\})', src, re.S)
    assert m, 'the %s helper moved' % name
    return m.group(1)


def _editable(service):
    stub = (
        'const _ownedChildNames = new Set();\n'
        + _fn('_svcBareName') + '\n'
        + _fn('_compositeTypeOf') + '\n'
        + _fn('_svcEditable') + '\n'
        + 'console.log(JSON.stringify(_svcEditable(' + json.dumps(service) + ')));'
    )
    out = subprocess.run(['node', '-e', stub], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip())


LB = {'loadBalancer': {'servers': [{'url': 'http://10.0.0.5:80'}]}}


def test_an_http_service_from_a_file_can_be_edited():
    assert _editable(dict(LB, name='web@file', _proto='HTTP')) is True


def test_a_service_with_no_protocol_is_treated_as_http():
    assert _editable(dict(LB, name='web@file')) is True


def test_a_tcp_service_cannot_be_edited():
    assert _editable(dict(LB, name='postgres@file', _proto='TCP')) is False, \
        'the service form only writes http services'


def test_a_udp_service_cannot_be_edited():
    assert _editable(dict(LB, name='wireguard@file', _proto='UDP')) is False


def test_a_service_from_another_provider_still_cannot_be_edited():
    assert _editable(dict(LB, name='web@docker', _proto='HTTP')) is False
