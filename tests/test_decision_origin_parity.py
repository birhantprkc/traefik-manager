import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def _host_origin():
    src = _read('app.py')
    m = re.search(r"'decisions': \[\{[^}]*'origin': '([a-z]+)'", src)
    assert m, 'the host decision payload moved'
    return m.group(1)


def _agent_origin():
    src = _read('agent', 'handlers.go')
    m = re.search(r'"duration": duration, "origin": "([a-z]+)"', src)
    assert m, 'the agent decision payload moved'
    return m.group(1)


def test_host_and_agent_record_the_same_origin():
    assert _host_origin() == _agent_origin(), \
        'a decision added by hand must look the same whichever server it was added on'


def test_the_origin_is_one_the_ui_counts_as_by_hand():
    src = _read('static', 'js', 'crowdsec.js')
    m = re.search(r'ATK_BY_HAND\s*=\s*\{([^}]*)\}', src)
    assert m, 'ATK_BY_HAND moved'
    by_hand = set(re.findall(r'(\w+):', m.group(1)))
    assert _host_origin() in by_hand, f'{_host_origin()} is not in {sorted(by_hand)}'
