import json

import core.settings as settings_mod
from conftest import read_config, write_config, post_form

from core import service_ownership as own


def _save(client, name, **extra):
    form = dict(serviceName=name, subdomain=f"{name}.example.com", protocol="http",
                scheme="http", targetIp="10.0.0.1", targetPort="8080",
                certResolver="letsencrypt")
    form.update(extra)
    return post_form(client, "/save", **form)


def _children(*rows, kind='weighted'):
    return json.dumps({'compositeType': kind, 'children': list(rows)})


def _manual(addr, weight=1, percent=0):
    return {'kind': 'manual', 'address': addr, 'scheme': 'http',
            'weight': weight, 'percent': percent}


def _ref(name, weight=1, percent=0):
    return {'kind': 'service', 'name': name, 'weight': weight, 'percent': percent}


def _svc(name=None):
    services = read_config()['http']['services']
    return services if name is None else services.get(name)


def test_posting_children_writes_a_weighted_service_with_per_row_weights(client):
    r = _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80', 9),
                                                        _manual('10.0.0.11:80', 1)))
    assert r.status_code < 400
    parent = _svc('api-service')
    assert parent['weighted']['services'] == [
        {'name': 'api-backend-1', 'weight': 9},
        {'name': 'api-backend-2', 'weight': 1},
    ]
    assert _svc('api-backend-1')['loadBalancer']['servers'] == [{'url': 'http://10.0.0.10:80'}]
    assert _svc('api-backend-2')['loadBalancer']['servers'] == [{'url': 'http://10.0.0.11:80'}]


def test_a_referenced_service_is_named_never_copied(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80'), _ref('canary-svc')))
    names = [s['name'] for s in _svc('api-service')['weighted']['services']]
    assert names == ['api-backend-1', 'canary-svc']
    assert 'canary-svc' not in _svc() or _svc('canary-svc') is None


def test_the_parent_and_children_are_recorded_in_the_ledger(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80')))
    ledger = settings_mod.load_settings().get('managed_middlewares') or {}
    assert own.ledger_key('api-service') in ledger
    assert own.ledger_key('api-backend-1') in ledger


def test_the_written_service_reads_back_as_owned(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80')))
    ledger = settings_mod.load_settings().get('managed_middlewares') or {}
    assert own.is_owned('api-service', _svc('api-service'), ledger)


def test_mirroring_and_failover_can_be_authored(client):
    _save(client, 'mir', backendsJsonHttp=_children(_manual('10.0.0.10:80'),
                                                    _ref('shadow', percent=10), kind='mirroring'))
    assert _svc('mir-service')['mirroring'] == {
        'service': 'mir-backend-1', 'mirrors': [{'name': 'shadow', 'percent': 10}]}

    _save(client, 'fo', backendsJsonHttp=_children(_manual('10.0.0.20:80'),
                                                   _ref('backup'), kind='failover'))
    assert _svc('fo-service')['failover'] == {'service': 'fo-backend-1', 'fallback': 'backup'}


def test_removing_every_child_reverts_to_a_plain_load_balancer(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80'), _manual('10.0.0.11:80')))
    assert 'weighted' in _svc('api-service')
    _save(client, 'api', backendsJsonHttp=json.dumps({'children': []}))
    parent = _svc('api-service')
    assert 'weighted' not in parent
    assert parent['loadBalancer']['servers'] == [{'url': 'http://10.0.0.1:8080'}]
    assert _svc('api-backend-1') is None
    assert _svc('api-backend-2') is None


def test_shrinking_the_row_count_drops_the_orphaned_child(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('a:80'), _manual('b:80'),
                                                    _manual('c:80')))
    assert _svc('api-backend-3') is not None
    _save(client, 'api', backendsJsonHttp=_children(_manual('a:80')))
    assert _svc('api-backend-2') is None
    assert _svc('api-backend-3') is None
    assert _svc('api-backend-1') is not None


def test_a_legacy_client_posting_no_children_key_does_not_destroy_the_composite(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80', 9),
                                                    _manual('10.0.0.11:80', 1)))
    before = read_config()['http']['services']['api-service']['weighted']
    _save(client, 'api', backendsJsonHttp=json.dumps({'servers': [{'url': 'http://10.0.0.1:8080'}]}))
    after = read_config()['http']['services'].get('api-service', {})
    assert 'weighted' in after, \
        'a client that never knew about children must not flatten the route'
    assert after['weighted'] == before


def test_a_client_posting_no_backends_json_at_all_does_not_destroy_the_composite(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80')))
    _save(client, 'api')
    assert 'weighted' in read_config()['http']['services']['api-service']


def test_a_mobile_shaped_edit_of_a_composite_is_not_rejected(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80')))
    r = post_form(client, "/save", serviceName='api', subdomain='api.example.com',
                  protocol='http', scheme='http', targetIp='', targetPort='',
                  certResolver='letsencrypt', originalName='api')
    assert r.status_code < 400, 'mobile posts no backendsJson and no target for a composite'


def test_a_brand_new_route_with_no_backend_is_still_rejected(client):
    r = post_form(client, "/save", serviceName='fresh', subdomain='fresh.example.com',
                  protocol='http', scheme='http', targetIp='', targetPort='',
                  certResolver='letsencrypt')
    assert r.status_code == 400, 'the mandatory backend guard must still fire for new routes'


def test_a_service_middlewares_sibling_survives_authoring(client):
    write_config("""
http:
  routers: {}
  services:
    api-service:
      loadBalancer:
        servers:
          - url: http://old:80
      middlewares:
        - secure@file
""")
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80')))
    parent = _svc('api-service')
    assert parent['middlewares'] == ['secure@file']
    assert 'weighted' in parent


def test_pass_host_header_survives_a_composite_save(client):
    _save(client, 'api', passHostHeader='', backendsJsonHttp=_children(_manual('10.0.0.10:80')))
    child = _svc('api-backend-1')['loadBalancer']
    assert child.get('passHostHeader') is False, \
        'the setting used to be read off the empty parent and lost'


def test_a_composite_route_reads_its_settings_back_from_its_child(client):
    _save(client, 'api', passHostHeader='', backendsJsonHttp=_children(_manual('10.0.0.10:80')))
    r = client.get('/api/routes')
    app_entry = next(a for a in r.get_json()['apps'] if a['name'] == 'api')
    assert app_entry['passHostHeader'] is False, \
        'the form used to be told True for every composite regardless'


def test_the_self_route_service_is_not_offered_as_a_backend(client):
    write_config("""
http:
  routers:
    traefik-manager:
      rule: Host(`tm.example.com`)
      service: traefik-manager
  services:
    traefik-manager:
      loadBalancer:
        servers:
          - url: http://traefik-manager:5000
    normal-service:
      loadBalancer:
        servers:
          - url: http://a:80
""")
    services = client.get('/api/routes').get_json()['services']['http']
    assert 'normal-service' in services
    assert 'traefik-manager' not in services, \
        'referencing the self route would break the Settings save path'


def test_the_ping_fallback_is_ssrf_checked(client, monkeypatch):
    import app as tm

    reached = []

    class _Resp:
        status_code = 200

    def fake_head(target, **kw):
        reached.append(target)
        if 'blocked' in target:
            return _Resp()
        raise OSError('primary is down')

    monkeypatch.setattr(tm.requests, 'head', fake_head)
    monkeypatch.setattr(tm, '_ssrf_ok', lambda u: 'blocked' not in u)

    r = client.get('/api/ping?url=http://allowed.example&fallback=http://blocked.example')
    assert not r.get_json().get('via_target'), 'a blocked fallback must not be fetched'
    assert 'http://blocked.example' not in reached, 'the blocked address was requested anyway'


def test_an_allowed_ping_fallback_is_still_used(client, monkeypatch):
    import app as tm

    class _Resp:
        status_code = 204

    def fake_head(target, **kw):
        if 'good' in target:
            return _Resp()
        raise OSError('primary is down')

    monkeypatch.setattr(tm.requests, 'head', fake_head)
    monkeypatch.setattr(tm, '_ssrf_ok', lambda u: True)

    r = client.get('/api/ping?url=http://bad.example&fallback=http://good.example')
    assert r.get_json().get('via_target') is True, 'the fallback must still work when allowed'


def test_the_services_endpoint_names_the_owned_children(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('a:80'), _manual('b:80')))
    body = client.get('/api/traefik/services').get_json()
    assert sorted(body['ownedChildren']) == ['api-backend-1', 'api-backend-2']


def test_a_referenced_service_is_never_listed_as_owned(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('a:80'), _ref('canary-svc')))
    body = client.get('/api/traefik/services').get_json()
    assert 'canary-svc' not in body['ownedChildren']
    assert 'api-service' not in body['ownedChildren'], 'the parent is not a child'


def test_owned_children_disappear_when_the_composite_is_reverted(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('a:80')))
    assert client.get('/api/traefik/services').get_json()['ownedChildren'] == ['api-backend-1']
    _save(client, 'api', backendsJsonHttp=json.dumps({'children': []}))
    assert client.get('/api/traefik/services').get_json()['ownedChildren'] == []


def _app_entry(client, name='api'):
    return next(a for a in client.get('/api/routes').get_json()['apps'] if a['name'] == name)


def test_an_authored_route_round_trips_its_children(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80', 9),
                                                    _ref('canary-svc', 1)))
    entry = _app_entry(client)
    assert entry['serviceType'] == 'weighted'
    assert [c['name'] for c in entry['compositeChildren']] == ['api-backend-1', 'canary-svc']
    assert [c['weight'] for c in entry['compositeChildren']] == [9, 1]
    assert entry['compositeChildren'][0]['url'] == 'http://10.0.0.10:80'
    assert entry['compositeChildren'][1]['url'] == '', 'a referenced service is not ours to inline'


def test_a_route_we_authored_is_reported_as_editable(client):
    _save(client, 'api', backendsJsonHttp=_children(_manual('10.0.0.10:80')))
    assert _app_entry(client)['serviceOwned'] is True


def test_a_hand_written_composite_is_not_reported_as_editable(client):
    write_config("""
http:
  routers:
    hand:
      rule: Host(`hand.example.com`)
      service: hand-pool
      entryPoints: [https]
  services:
    hand-pool:
      weighted:
        services:
          - name: a-svc
            weight: 1
    a-svc:
      loadBalancer:
        servers:
          - url: http://a:80
""")
    entry = _app_entry(client, 'hand')
    assert entry['serviceType'] == 'weighted'
    assert entry['serviceOwned'] is False, 'a hand written composite must stay read only'
    assert [c['name'] for c in entry['compositeChildren']] == ['a-svc']


def test_mirroring_round_trips_its_percentages(client):
    _save(client, 'mir', backendsJsonHttp=_children(_manual('a:80'), _ref('shadow', percent=25),
                                                    kind='mirroring'))
    entry = _app_entry(client, 'mir')
    assert entry['serviceType'] == 'mirroring'
    assert [c['percent'] for c in entry['compositeChildren']] == [0, 25]


def test_failover_round_trips_both_halves(client):
    _save(client, 'fo', backendsJsonHttp=_children(_manual('a:80'), _ref('backup'),
                                                   kind='failover'))
    entry = _app_entry(client, 'fo')
    assert [c['name'] for c in entry['compositeChildren']] == ['fo-backend-1', 'backup']


def test_a_plain_route_reports_no_composite_children(client):
    _save(client, 'plain')
    entry = _app_entry(client, 'plain')
    assert entry['compositeChildren'] == []
    assert entry['serviceOwned'] is False


def _own(client, name, adopt):
    return client.post(f'/api/services/{name}/ownership', json={'adopt': adopt},
                       headers={'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'})


HAND_WRITTEN = """
http:
  routers:
    hand:
      rule: Host(`hand.example.com`)
      service: hand-pool
      entryPoints: [https]
  services:
    hand-pool:
      weighted:
        services:
          - name: a-svc
            weight: 1
        sticky:
          cookie:
            name: lb
    a-svc:
      loadBalancer:
        servers:
          - url: http://a:80
"""


def test_a_hand_written_composite_can_be_adopted(client):
    write_config(HAND_WRITTEN)
    assert _app_entry(client, 'hand')['serviceOwned'] is False
    r = _own(client, 'hand-pool', True)
    assert r.status_code == 200 and r.get_json()['owned'] is True
    assert _app_entry(client, 'hand')['serviceOwned'] is True


def test_adopting_touches_no_yaml(client):
    write_config(HAND_WRITTEN)
    before = read_config()['http']['services']['hand-pool']
    _own(client, 'hand-pool', True)
    assert read_config()['http']['services']['hand-pool'] == before


def test_an_adopted_service_keeps_settings_we_do_not_author(client):
    write_config(HAND_WRITTEN)
    _own(client, 'hand-pool', True)
    _save(client, 'hand', originalName='hand',
          backendsJsonHttp=_children(_manual('10.0.0.9:80')))
    weighted = read_config()['http']['services']['hand-pool']['weighted']
    assert weighted['sticky'] == {'cookie': {'name': 'lb'}}, \
        'adopting must not become a licence to destroy what we cannot express'


def test_management_can_be_released(client):
    write_config(HAND_WRITTEN)
    _own(client, 'hand-pool', True)
    r = _own(client, 'hand-pool', False)
    assert r.status_code == 200 and r.get_json()['owned'] is False
    assert _app_entry(client, 'hand')['serviceOwned'] is False


def test_a_plain_load_balancer_cannot_be_adopted(client):
    _save(client, 'plain')
    r = _own(client, 'plain-service', True)
    assert r.status_code == 400


def test_adopting_something_that_does_not_exist_is_a_404(client):
    assert _own(client, 'nope', True).status_code == 404


def test_the_services_endpoint_lists_managed_parents(client):
    write_config(HAND_WRITTEN)
    _own(client, 'hand-pool', True)
    body = client.get('/api/traefik/services').get_json()
    assert 'hand-pool' in body['ownedServices']
    assert 'hand-pool' not in body['ownedChildren'], 'a parent is not a child'
