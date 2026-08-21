import app as app_mod


class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError('http error')


def _reset():
    app_mod._PLUGIN_CATALOG['ts'] = 0.0
    app_mod._PLUGIN_CATALOG['map'] = {}


def test_catalog_returns_a_slim_module_map(client, monkeypatch):
    _reset()
    monkeypatch.setattr('app.requests.get', lambda *a, **k: _Resp([
        {'import': 'github.com/Org/Plugin', 'latestVersion': 'v2.0.0', 'readme': 'x' * 9000},
        {'import': 'github.com/other/thing', 'latestVersion': 'v1.1.0'},
        {'import': '', 'latestVersion': 'v9'},
    ]))
    d = client.get('/api/plugins/catalog').get_json()
    assert d['plugins'] == {'github.com/org/plugin': 'v2.0.0',
                            'github.com/other/thing': 'v1.1.0'}


def test_catalog_is_cached_between_requests(client, monkeypatch):
    _reset()
    calls = []
    monkeypatch.setattr('app.requests.get',
                        lambda *a, **k: calls.append(1) or _Resp([
                            {'import': 'github.com/a/b', 'latestVersion': 'v1.0.0'}]))
    client.get('/api/plugins/catalog')
    client.get('/api/plugins/catalog')
    assert len(calls) == 1, 'the catalog must be fetched once, not per request'


def test_catalog_failure_returns_empty_not_error(client, monkeypatch):
    _reset()
    def boom(*a, **k):
        raise RuntimeError('offline')
    monkeypatch.setattr('app.requests.get', boom)
    r = client.get('/api/plugins/catalog')
    assert r.status_code == 200
    assert r.get_json()['plugins'] == {}
