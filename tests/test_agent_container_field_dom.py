import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODAL = os.path.join(ROOT, 'templates', 'modals', 'settings_modal.html')
JS = os.path.join(ROOT, 'static', 'js', 'settings-modal.js')


def _modal():
    with open(MODAL, encoding='utf-8') as fh:
        return fh.read()


def _js():
    with open(JS, encoding='utf-8') as fh:
        return fh.read()


def test_there_is_exactly_one_container_input():
    assert _modal().count('id="agCfgContainer"') == 1
    assert 'agCfgSocketContainer' not in _modal(), \
        'a second container input is never read, so typing in it is silently ignored'


def test_nothing_references_the_removed_input():
    assert 'agCfgSocketContainer' not in _js()


def test_the_container_field_lives_outside_the_proxy_pane():
    html = _modal()
    proxy = html.index('id="restartProxyFields"')
    field = html.index('id="restartContainerField"')
    assert field > proxy, 'the shared field must not sit inside one method pane'
    pane_end = html.index('id="restartPoisonPillFields"')
    assert not (proxy < html.index('id="agCfgContainer"') < pane_end), \
        'the container input is still nested in the proxy pane'


def test_the_field_is_shown_for_both_docker_methods():
    body = _js().split('function selectRestartMethod', 1)[1].split('\n}', 1)[0]
    assert 'restartContainerField' in body
    assert re.search(r"proxy'\s*\|\|\s*method === 'socket'", body), \
        'the container name applies to socket proxy and direct socket alike'


def test_every_dom_read_uses_the_one_field_with_no_fallback_chain():
    reads = [line.strip() for line in _js().split('\n')
             if "getElementById('agCfgContainer')" in line]
    assert len(reads) >= 3, reads
    for line in reads:
        assert line.count('getElementById(') == 1, \
            'a fallback chain means one of the inputs is dead: %s' % line
