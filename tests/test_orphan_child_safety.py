import json

from conftest import read_config, write_config, post_form

HDR = {'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'}


def _manual(addr, weight=1):
    return {'kind': 'manual', 'address': addr, 'scheme': 'http', 'weight': weight, 'percent': 0}


def _save(client, name, children, kind='weighted', **extra):
    body = {'name': name, 'type': kind, 'children': children}
    body.update(extra)
    return client.post('/api/services', json=body, headers=HDR)


def _svcs():
    return sorted((read_config().get('http') or {}).get('services') or {})


def _routers():
    return {k: v.get('service')
            for k, v in ((read_config().get('http') or {}).get('routers') or {}).items()}


def test_deleting_a_parent_does_not_break_a_route_using_its_child(client):
    assert _save(client, 'p', [_manual('10.0.0.1:80'), _manual('10.0.0.2:80')]).status_code == 200
    post_form(client, '/save', serviceName='live', subdomain='live.example.com',
              protocol='http', scheme='http', certResolver='letsencrypt',
              targetIp='10.0.0.1', targetPort='8080', serviceRef='p-backend-1')
    assert _routers().get('live') == 'p-backend-1', 'the child is offered by the route picker'

    r = client.delete('/api/services/p', headers=HDR)
    assert r.status_code == 409, \
        'deleting p silently deletes p-backend-1, which the live route serves from'
    assert 'p-backend-1' in _svcs()


def test_deleting_a_parent_does_not_break_another_composite_using_its_child(client):
    assert _save(client, 'p', [_manual('10.0.0.1:80'), _manual('10.0.0.2:80')]).status_code == 200
    assert _save(client, 'q', [{'kind': 'service', 'name': 'p-backend-1', 'weight': 1,
                                'percent': 0}]).status_code == 200
    r = client.delete('/api/services/p', headers=HDR)
    assert r.status_code == 409, 'q still references p-backend-1'
    assert 'p-backend-1' in _svcs()


def test_a_service_cannot_overwrite_another_services_children(client):
    post_form(client, '/save', serviceName='api', subdomain='api.example.com',
              protocol='http', scheme='http', certResolver='letsencrypt',
              targetIp='10.0.0.1', targetPort='8080',
              backendsJsonHttp=json.dumps({'compositeType': 'weighted', 'children': [
                  _manual('10.0.0.10:80'), _manual('10.0.0.11:80')]}))
    before = (read_config().get('http') or {}).get('services') or {}
    assert 'api-backend-1' in before and 'api-backend-2' in before

    r = _save(client, 'api', [_manual('10.9.9.1:80')])
    after = (read_config().get('http') or {}).get('services') or {}
    assert r.status_code == 409, 'api-backend-* already belongs to api-service'
    assert after.get('api-backend-1') == before['api-backend-1'], 'the route backend was overwritten'
    assert 'api-backend-2' in after, 'the route backend was deleted'


def test_a_name_cannot_adopt_an_orphaned_child_of_another_parent(client):
    post_form(client, '/save', serviceName='api', subdomain='api.example.com',
              protocol='http', scheme='http', certResolver='letsencrypt',
              targetIp='10.0.0.1', targetPort='8080',
              backendsJsonHttp=json.dumps({'compositeType': 'weighted', 'children': [
                  _manual('10.0.0.10:80'), _manual('10.0.0.11:80')]}))
    cfg = read_config()
    services = (cfg.get('http') or {}).get('services') or {}
    del services['api-service']
    del cfg['http']['routers']['api']
    import io as _io
    from core import config as _c
    buf = _io.StringIO()
    _c.yaml.dump(cfg, buf)
    write_config(buf.getvalue())
    assert 'api-backend-1' in ((read_config().get('http') or {}).get('services') or {}), \
        'the children are now orphans, referenced by nothing'

    before = ((read_config().get('http') or {}).get('services') or {})['api-backend-1']
    r = _save(client, 'api', [_manual('10.9.9.1:80')])
    after = (read_config().get('http') or {}).get('services') or {}
    assert r.status_code == 409, 'api-backend-1 is still recorded as belonging to api-service'
    assert after.get('api-backend-1') == before, 'the orphan was silently overwritten'


def test_shrinking_a_composite_does_not_drop_a_child_in_use(client):
    assert _save(client, 'p', [_manual('10.0.0.1:80'), _manual('10.0.0.2:80'),
                               _manual('10.0.0.3:80')]).status_code == 200
    post_form(client, '/save', serviceName='live', subdomain='live.example.com',
              protocol='http', scheme='http', certResolver='letsencrypt',
              targetIp='10.0.0.1', targetPort='8080', serviceRef='p-backend-3')
    assert _routers().get('live') == 'p-backend-3'

    r = _save(client, 'p', [_manual('10.0.0.1:80'), _manual('10.0.0.2:80')])
    assert r.status_code == 409, \
        'shrinking p drops p-backend-3, which the live route serves from'
    assert 'p-backend-3' in _svcs()


def test_a_route_refuses_a_third_failover_backend(client):
    r = post_form(client, '/save', serviceName='fo', subdomain='fo.example.com',
                  protocol='http', scheme='http', certResolver='letsencrypt',
                  targetIp='10.0.0.1', targetPort='8080',
                  backendsJsonHttp=json.dumps({'compositeType': 'failover', 'children': [
                      _manual('10.0.0.1:80'), _manual('10.0.0.2:80'), _manual('10.0.0.3:80')]}))
    assert r.status_code >= 400, \
        'the third backend is silently discarded with a success message'
    body = r.get_json() or {}
    assert 'failover' in (body.get('message') or body.get('error') or '').lower()
