import core.settings as settings_mod
from conftest import read_config, write_config


def _ledger(entries):
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=s['auth_enabled'],
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        managed_middlewares=entries)


def _delete(client, rid):
    return client.post('/delete/' + rid, headers={'X-CSRF-Token': 'testtoken',
                                                  'X-Requested-With': 'fetch'})


OWNED = """
http:
  routers:
    app1:
      rule: Host(`app1.example.com`)
      service: app1-service
  services:
    app1-service:
      loadBalancer:
        servers: [{url: 'https://10.0.0.1:443'}]
        serversTransport: app1-service-transport
  serversTransports:
    app1-service-transport:
      insecureSkipVerify: true
"""


def test_deleting_a_route_removes_the_transport_it_owns(client):
    write_config(OWNED)
    _ledger({'tp::app1-service-transport': {'kind': 'route-transport', 'route': 'app1'}})
    assert _delete(client, 'app1').status_code < 400
    cfg = read_config()
    assert 'serversTransports' not in cfg.get('http', {}), 'the owned transport must go with the route'
    assert 'tp::app1-service-transport' not in settings_mod.load_settings()['managed_middlewares']


def test_a_hand_written_transport_is_left_alone(client):
    write_config(OWNED)
    _ledger({})
    assert _delete(client, 'app1').status_code < 400
    assert 'app1-service-transport' in read_config()['http']['serversTransports'], \
        'without a ledger entry the transport is the user\'s, not ours'


def test_a_transport_another_service_still_uses_is_kept(client):
    write_config("""
http:
  routers:
    app1:
      rule: Host(`app1.example.com`)
      service: app1-service
    app2:
      rule: Host(`app2.example.com`)
      service: app2-service
  services:
    app1-service:
      loadBalancer:
        servers: [{url: 'https://10.0.0.1:443'}]
        serversTransport: app1-service-transport
    app2-service:
      loadBalancer:
        servers: [{url: 'https://10.0.0.2:443'}]
        serversTransport: app1-service-transport
  serversTransports:
    app1-service-transport:
      insecureSkipVerify: true
""")
    _ledger({'tp::app1-service-transport': {'kind': 'route-transport', 'route': 'app1'}})
    assert _delete(client, 'app1').status_code < 400
    assert 'app1-service-transport' in read_config()['http']['serversTransports'], \
        'app2-service still points at it'


def test_a_disabled_routes_snapshot_protects_the_transport(client):
    write_config(OWNED)
    _ledger({'tp::app1-service-transport': {'kind': 'route-transport', 'route': 'app1'}})
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=s['auth_enabled'],
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        managed_middlewares=s['managed_middlewares'],
        disabled_routes={'other': {'protocol': 'http', 'router': {'service': 'other-service'},
                                   'service': {'loadBalancer': {
                                       'serversTransport': 'app1-service-transport'}},
                                   'configFile': 'dynamic.yml'}})
    assert _delete(client, 'app1').status_code < 400
    assert 'app1-service-transport' in read_config()['http']['serversTransports'], \
        'a disabled route would come back broken'


def test_the_service_itself_still_goes(client):
    write_config(OWNED)
    _ledger({'tp::app1-service-transport': {'kind': 'route-transport', 'route': 'app1'}})
    assert _delete(client, 'app1').status_code < 400
    cfg = read_config()
    assert 'app1-service' not in (cfg.get('http', {}).get('services') or {})
    assert 'app1' not in (cfg.get('http', {}).get('routers') or {})
