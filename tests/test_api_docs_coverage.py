import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UNDOCUMENTED_BY_DESIGN = set()


def _api_routes():
    src = open(os.path.join(ROOT, 'app.py')).read()
    routes = set()
    for m in re.finditer(r"@app\.route\(\s*'([^']+)'(?:\s*,\s*methods\s*=\s*\[([^\]]+)\])?", src):
        path = m.group(1)
        if not path.startswith('/api/'):
            continue
        for meth in re.findall(r"'(\w+)'", m.group(2) or "'GET'"):
            routes.add((meth, path))
    return routes


def _normalise(path):
    return re.sub(r'<[^>]+>', '{}', path).replace('//', '/').rstrip('/')


def _present(path, text):
    stripped = re.sub(r'\{[^}]*\}', '{}', text)
    return _normalise(path) in stripped


def test_every_api_route_is_in_openapi():
    spec = open(os.path.join(ROOT, 'static/openapi.yaml')).read()
    missing = sorted(f'{m} {p}' for m, p in _api_routes()
                     if p not in UNDOCUMENTED_BY_DESIGN and not _present(p, spec))
    assert not missing, ('endpoints missing from static/openapi.yaml:\n  '
                         + '\n  '.join(missing))


def test_every_api_route_is_in_api_md():
    doc = open(os.path.join(ROOT, 'docs/api.md')).read()
    missing = sorted(f'{m} {p}' for m, p in _api_routes()
                     if p not in UNDOCUMENTED_BY_DESIGN and not _present(p, doc))
    assert not missing, ('endpoints missing from docs/api.md:\n  '
                         + '\n  '.join(missing))


def test_every_agent_route_is_documented():
    main = open(os.path.join(ROOT, 'agent/main.go')).read()
    paths = set(re.findall(r'p == "(/api/[^"]+)"', main))
    paths |= set(re.findall(r'strings\.HasPrefix\(p, "(/api/[^"]+)"', main))
    doc = open(os.path.join(ROOT, 'docs/api-agent.md')).read()
    missing = sorted(p for p in paths if p.rstrip('/') not in doc)
    assert not missing, ('endpoints missing from docs/api-agent.md:\n  '
                         + '\n  '.join(missing))


def test_published_openapi_matches_the_served_one():
    served = open(os.path.join(ROOT, 'static/openapi.yaml')).read()
    published = open(os.path.join(ROOT, 'docs/public/openapi.yaml')).read()
    assert served == published, 'static/openapi.yaml and docs/public/openapi.yaml have drifted'


def test_api_docs_state_the_401_contract():
    doc = open(os.path.join(ROOT, 'docs/api.md')).read()
    assert '401' in doc
    assert 'auth_required' in doc
