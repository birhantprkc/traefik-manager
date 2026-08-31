import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = os.path.join(ROOT, 'static', 'js', 'services.js')


def _composite_expression():
    with open(JS, encoding='utf-8') as fh:
        src = fh.read()
    m = re.search(r'const composite = (.*?);\n', src, re.S)
    assert m, 'the composite children expression moved'
    return m.group(1)


def _run(service):
    expr = _composite_expression()
    script = (
        'const s = ' + service + ';\n'
        'const composite = ' + expr + ';\n'
        'console.log(JSON.stringify(composite));\n'
    )
    out = subprocess.run(['node', '-e', script], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    import json
    return json.loads(out.stdout)


def test_a_mirror_always_shows_its_share():
    out = _run('{"mirroring": {"service": "main", "mirrors": [{"name": "shadow", "percent": 10}]}}')
    assert out == ['main', 'shadow mirror (10%)']


def test_a_mirror_with_no_percent_shows_zero_because_it_gets_no_traffic():
    out = _run('{"mirroring": {"service": "main", "mirrors": [{"name": "shadow"}]}}')
    assert out == ['main', 'shadow mirror (0%)'], \
        'percent defaults to 0 in Traefik, so a mirror without it receives nothing'


def test_highest_random_weight_children_are_listed():
    out = _run('{"highestRandomWeight": {"services": [{"name": "a"}, {"name": "b", "weight": 3}]}}')
    assert out == ['a', 'b (3)'], 'an HRW service used to render with no children at all'


def test_weighted_children_still_show_their_weight():
    out = _run('{"weighted": {"services": [{"name": "blue", "weight": 1}, {"name": "green"}]}}')
    assert out == ['blue (1)', 'green']


def test_failover_shows_both_halves():
    out = _run('{"failover": {"service": "primary", "fallback": "backup"}}')
    assert out == ['primary', 'backup fallback']


def test_a_plain_load_balancer_has_no_composite_children():
    assert _run('{"loadBalancer": {"servers": [{"url": "http://a:80"}]}}') == []
