import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, 'static', 'js', 'core.js')

PAYLOADS = [
    "m');alert(1);//",
    'm");alert(1);//',
    "m\\');alert(1);//",
    "</script><img src=x onerror=alert(1)>",
    "a&#39;);alert(1);//",
    "plain-name",
    "name with 'both' \"quotes\"",
]


def _fn(name, src):
    m = re.search(r'(function ' + name + r'\(.*?\n\})', src, re.S)
    assert m, 'the %s helper moved' % name
    return m.group(1)


def _render(values):
    with open(CORE, encoding='utf-8') as fh:
        src = fh.read()
    stub = (_fn('_esc', src) + '\n' + _fn('_jsArg', src) + '\n'
            + 'const out = ' + json.dumps(values)
            + '.map(v => `<button onclick="f(${_jsArg(v)})">x</button>`);\n'
              'console.log(JSON.stringify(out));')
    r = subprocess.run(['node', '-e', stub], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class _Attr:
    def __init__(self, markup):
        from html.parser import HTMLParser

        got = {}

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                got.update(dict(attrs))

        P().feed(markup)
        self.onclick = got.get('onclick', '')


CALL = re.compile(r'^f\((".*")\)$', re.S)


def test_no_payload_escapes_the_js_string():
    for value, markup in zip(PAYLOADS, _render(PAYLOADS)):
        onclick = _Attr(markup).onclick
        m = CALL.match(onclick)
        assert m, 'the value broke out of the call: %r -> %r' % (value, onclick)
        assert json.loads(m.group(1)) == value, \
            'the value did not survive the round trip: %r -> %r' % (value, onclick)


def test_the_old_pattern_is_actually_vulnerable():
    with open(CORE, encoding='utf-8') as fh:
        src = fh.read()
    stub = (_fn('_esc', src)
            + "\nconsole.log(`<button onclick=\"f('${_esc(\"m');alert(1);//\")}')\">x</button>`);")
    r = subprocess.run(['node', '-e', stub], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    onclick = _Attr(r.stdout.strip()).onclick
    assert onclick == "f('m');alert(1);//')", \
        'if this changes, _esc gained JS-string escaping and _jsArg may be redundant'


def test_no_inline_handler_passes_a_string_through_esc():
    offenders = []
    js_dir = os.path.join(ROOT, 'static', 'js')
    for fname in sorted(os.listdir(js_dir)):
        if not fname.endswith('.js'):
            continue
        with open(os.path.join(js_dir, fname), encoding='utf-8') as fh:
            for n, line in enumerate(fh, 1):
                for handler in re.findall(r'on\w+="[^"]*"', line):
                    if re.search(r"'\$\{_esc\(", handler):
                        offenders.append('%s:%d' % (fname, n))
    assert not offenders, (
        'inline handlers must use ${_jsArg(v)}, not \'${_esc(v)}\' - '
        'the HTML parser decodes &#39; back to a quote before the JS is compiled. '
        'Offenders: ' + ', '.join(offenders))
