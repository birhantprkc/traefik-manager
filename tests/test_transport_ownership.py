import core.settings as settings_mod
from conftest import DYNAMIC_PATH, post_form, write_config


HAND_WRITTEN = """http:
  routers:
    Nextcloud:
      rule: Host(`cloud.example.com`)
      service: Nextcloud
      entryPoints: [websecure]
  services:
    Nextcloud:
      loadBalancer:
        servers:
          - url: https://10.0.0.5:443
        serversTransport: Nextcloud-transport
  serversTransports:
    Nextcloud-transport:
      insecureSkipVerify: true
      forwardingTimeouts:
        dialTimeout: 30s
        responseHeaderTimeout: 300s
        idleConnTimeout: 3600s
"""


def _save(client, **extra):
    data = {
        'appName': 'Nextcloud', 'domain': 'cloud.example.com',
        'targetIp': '10.0.0.5', 'targetPort': '443',
        'isEdit': 'true', 'originalId': 'Nextcloud',
        'protocol': 'http', 'entryPoints': 'websecure',
        'serviceName': 'Nextcloud',
    }
    data.update(extra)
    res = post_form(client, '/save', **data)
    assert res.status_code == 200, res.get_data(as_text=True)
    return res


def _transports():
    import core.config as cfg
    return (cfg.load_config(str(DYNAMIC_PATH)).get('http', {}) or {}).get('serversTransports', {})


def test_a_hand_written_transport_survives_a_route_save(client):
    write_config(HAND_WRITTEN)

    _save(client)

    tp = _transports().get('Nextcloud-transport')
    assert tp is not None, 'the hand written transport was deleted'
    assert tp.get('insecureSkipVerify') is True, 'insecureSkipVerify was stripped'
    ft = tp.get('forwardingTimeouts') or {}
    assert ft.get('dialTimeout') == '30s', 'forwardingTimeouts was overwritten'
    assert ft.get('responseHeaderTimeout') == '300s'
    assert ft.get('idleConnTimeout') == '3600s'


def test_the_service_still_references_the_transport(client):
    import core.config as cfg
    write_config(HAND_WRITTEN)

    _save(client)

    svc = cfg.load_config(str(DYNAMIC_PATH))['http']['services']['Nextcloud']['loadBalancer']
    assert svc.get('serversTransport') == 'Nextcloud-transport'


def test_a_transport_we_created_is_still_ours_to_remove(client):
    s = settings_mod.load_settings()
    assert isinstance(s.get('managed_middlewares', {}), dict)


def test_the_streaming_preset_does_not_wipe_hand_written_timeouts(client):
    write_config(HAND_WRITTEN)

    _save(client, streamingPresetPresent='true', streamingPresetEnabled='false')

    tp = _transports().get('Nextcloud-transport')
    assert tp is not None, 'the transport was deleted by the streaming preset'
    ft = tp.get('forwardingTimeouts') or {}
    assert ft.get('responseHeaderTimeout') == '300s', 'forwardingTimeouts was wiped'
    assert ft.get('idleConnTimeout') == '3600s'
