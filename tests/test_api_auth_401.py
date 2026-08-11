import json


def test_api_returns_401_json_not_a_redirect(anon_client):
    r = anon_client.get('/api/crowdsec/decisions')
    assert r.status_code == 401
    body = json.loads(r.data)
    assert body.get('auth_required') is True


def test_api_401_is_not_parseable_as_an_empty_list(anon_client):
    r = anon_client.get('/api/backups')
    assert r.status_code == 401
    assert json.loads(r.data) != []


def test_every_api_get_refuses_anonymously_with_401(anon_client):
    for path in ('/api/backups', '/api/agents', '/api/mw/templates',
                 '/api/traefik/routers', '/api/crowdsec/alerts'):
        r = anon_client.get(path)
        assert r.status_code == 401, path
        assert r.headers.get('Location') is None, path


def test_page_routes_still_redirect_to_login(anon_client):
    r = anon_client.get('/')
    assert r.status_code == 302
    assert '/login' in r.headers.get('Location', '')
