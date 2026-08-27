"""Which header-strategy key the entry point form writes.

underscoreHeadersStrategy exists from Traefik v3.7.6, aliasHeadersStrategy from
v3.7.12, and neither exists anywhere in 3.6.x. Writing a key the running Traefik
does not know is not ignored: it refuses to start with
"field not found, node: <key>", which takes the proxy down until the file is
edited by hand.
"""
import pytest

from conftest import post_json

JS = 'static/js/static-config.js'


def _js(app_module):
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, JS), encoding='utf-8') as fh:
        return fh.read()


def test_underscore_gate_no_longer_claims_3_6_support(app_module):
    """3.6.20 and 3.6.21 both lack the option; the old gate said 3.6.20+ had it."""
    src = _js(app_module)
    body = src.split('function _traefikSupportsUnderscoreStrategy', 1)[1].split('\n}', 1)[0]
    assert 'min === 6' not in body, \
        'no 3.6.x release has underscoreHeadersStrategy - offering it there bricks Traefik'
    assert 'pat >= 6' in body, 'underscoreHeadersStrategy starts at 3.7.6'


def test_alias_gate_starts_at_3_7_12(app_module):
    src = _js(app_module)
    assert 'function _traefikSupportsAliasStrategy' in src
    body = src.split('function _traefikSupportsAliasStrategy', 1)[1].split('\n}', 1)[0]
    assert 'pat >= 12' in body, 'aliasHeadersStrategy starts at 3.7.12'
    assert 'min === 6' not in body


@pytest.mark.parametrize('key', ['aliasHeadersStrategy', 'underscoreHeadersStrategy'])
def test_the_form_writes_the_requested_key(client, config_path, key):
    r = post_json(client, '/api/static/section', {
        'action': 'set', 'section': 'entrypoints', 'name': 'websecure',
        'current_raw': 'entryPoints: {}\n',
        'data': {'address': ':443', 'underscore_headers': 'delete',
                 'headers_strategy_key': key},
    })
    assert r.status_code < 400, r.get_data(as_text=True)


def test_only_one_of_the_two_keys_is_ever_written(client):
    """Traefik deprecates the old name but still accepts it - both at once is ambiguous."""
    post_json(client, '/api/static/section', {
        'action': 'set', 'section': 'entrypoints', 'name': 'websecure',
        'current_raw': 'entryPoints: {}\n',
        'data': {'address': ':443', 'underscore_headers': 'delete',
                 'headers_strategy_key': 'underscoreHeadersStrategy'},
    })
    r = post_json(client, '/api/static/section', {
        'action': 'set', 'section': 'entrypoints', 'name': 'websecure',
        'current_raw': 'entryPoints:\n  websecure:\n    address: ":443"\n    http:\n      underscoreHeadersStrategy: delete\n',
        'data': {'address': ':443', 'underscore_headers': 'delete',
                 'headers_strategy_key': 'aliasHeadersStrategy'},
    })
    assert r.status_code < 400, r.get_data(as_text=True)
    body = r.get_json().get('raw', '') or r.get_data(as_text=True)
    assert 'aliasHeadersStrategy' in body
    assert 'underscoreHeadersStrategy' not in body, \
        'switching to the new key must remove the old one'


def test_an_unknown_key_falls_back_to_the_safe_old_name(client):
    r = post_json(client, '/api/static/section', {
        'action': 'set', 'section': 'entrypoints', 'name': 'websecure',
        'current_raw': 'entryPoints: {}\n',
        'data': {'address': ':443', 'underscore_headers': 'delete',
                 'headers_strategy_key': 'somethingElse'},
    })
    assert r.status_code < 400, r.get_data(as_text=True)
    body = r.get_json().get('raw', '') or r.get_data(as_text=True)
    assert 'underscoreHeadersStrategy' in body
    assert 'aliasHeadersStrategy' not in body
