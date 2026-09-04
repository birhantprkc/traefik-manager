import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, 'static', 'js', 'routes.js')


def _src():
    with open(JS, encoding='utf-8') as fh:
        return fh.read()


def _fn(name, src):
    m = re.search(r'(function ' + name + r'\(.*?\n\})', src, re.S)
    assert m, 'the %s helper moved' % name
    return m.group(1)


def _decide(any_service_row, loaded_as_composite):
    src = _src()
    m = re.search(r"if \(proto === 'http' && \((.+?)\)\) \{\n\s*payload\.children", src)
    assert m, 'the children-posting condition moved'
    stub = (
        'let _routeWasComposite = %s;\n' % ('true' if loaded_as_composite else 'false')
        + 'const _bkAnyServiceRow = () => %s;\n' % ('true' if any_service_row else 'false')
        + 'console.log(JSON.stringify(!!(%s)));' % m.group(1)
    )
    out = subprocess.run(['node', '-e', stub], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_a_route_with_a_service_row_posts_its_children():
    assert _decide(any_service_row=True, loaded_as_composite=False) is True


def test_a_composite_route_posts_children_after_its_last_service_row_is_removed():
    assert _decide(any_service_row=False, loaded_as_composite=True) is True, \
        'removing the last service row must still reach the backend, or the edit is discarded'


def test_a_plain_route_still_posts_no_children():
    assert _decide(any_service_row=False, loaded_as_composite=False) is False, \
        'a plain load balancer must not be turned into a composite'


def test_the_flag_resets_when_the_form_opens_and_when_a_route_loads():
    src = _src()
    opens = _fn('openModal', src) if 'function openModal' in src else ''
    m = re.search(r'(async function openModal\(.*?\n\})', src, re.S)
    if m:
        opens = m.group(1)
    assert '_routeWasComposite = false' in opens, \
        'opening a fresh route form must clear the composite flag'
    load = _fn('_loadCompositeRows', src)
    assert '_routeWasComposite = false' in load, \
        'loading a route must clear the flag before deciding'
    assert '_routeWasComposite = true' in load
