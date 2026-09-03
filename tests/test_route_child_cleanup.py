import json

import core.settings as settings_mod
from conftest import read_config, post_form

HDR = {'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'}


def _manual(addr, weight=1):
    return {'kind': 'manual', 'address': addr, 'scheme': 'http', 'weight': weight, 'percent': 0}


def _children(*rows, kind='weighted'):
    return json.dumps({'compositeType': kind, 'children': list(rows)})


def _route(client, name, **extra):
    form = dict(serviceName=name, subdomain=f'{name}.example.com', protocol='http',
                scheme='http', targetIp='10.0.0.1', targetPort='8080',
                certResolver='letsencrypt')
    form.update(extra)
    return post_form(client, '/save', **form)


def _svcs():
    return sorted((read_config().get('http') or {}).get('services') or {})


def _ledger_keys():
    ledger = settings_mod.load_settings().get('managed_middlewares') or {}
    return sorted(k for k in ledger if k.startswith('svc::'))


def test_deleting_a_route_takes_its_owned_children_with_it(client):
    _route(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80'),
                                                     _manual('10.0.0.11:80')))
    assert 'api-backend-1' in _svcs()

    client.post('/delete/api', headers=HDR)
    assert _svcs() == [], 'the composite children were left behind as orphans: %r' % _svcs()
    assert _ledger_keys() == [], 'stale ledger entries hide the orphans from the services tab'


def test_renaming_a_route_moves_its_children(client):
    _route(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80'),
                                                     _manual('10.0.0.11:80')))
    _route(client, 'web', isEdit='true', originalId='api',
           backendsJsonHttp=_children(_manual('10.0.0.10:80'), _manual('10.0.0.11:80')))

    http = read_config().get('http') or {}
    parent = (http.get('routers') or {}).get('web', {}).get('service')
    assert parent, 'the renamed router lost its service'
    assert parent in _svcs(), 'the renamed router points at a service that does not exist'

    orphans = [s for s in _svcs() if s.startswith('api-backend-')]
    assert orphans == [], 'the old route name left orphaned children behind: %r' % orphans
    assert not [k for k in _ledger_keys() if k.startswith('svc::api-backend-')], \
        'stale ledger entries for the old children: %r' % _ledger_keys()

    kids = [c['name'] for c in (http['services'][parent].get('weighted') or {}).get('services', [])]
    assert all(k in _svcs() for k in kids), 'the parent references a child that was deleted'



def test_a_ledger_entry_for_a_vanished_service_is_pruned(client):
    _route(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80'),
                                                     _manual('10.0.0.11:80')))
    assert _ledger_keys(), 'the route should have recorded ownership'

    cfg = read_config()
    del cfg['http']['services']['api-backend-1']
    import io as _io

    from core import config as _c
    buf = _io.StringIO()
    _c.yaml.dump(cfg, buf)
    from conftest import write_config as _w
    _w(buf.getvalue())

    client.get('/api/traefik/services')
    keys = _ledger_keys()
    assert 'svc::api-backend-1' not in keys, \
        'a hand-deleted service leaves a ledger entry that hides it from the services tab: %r' % keys


def test_a_broken_config_file_does_not_prune_the_ledger(client):
    _route(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80'),
                                                     _manual('10.0.0.11:80')))
    before = _ledger_keys()
    assert before

    from conftest import write_config as _w
    _w('http:\n  services:\n    broken: [oops\n')

    r = client.get('/api/traefik/services')
    assert r.status_code == 200, \
        'a config that fails to parse must not break the services list'
    assert _ledger_keys() == before, \
        'a config that failed to parse must not be read as "these services are gone"'
