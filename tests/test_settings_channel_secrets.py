from conftest import post_json
from core import settings as settings_mod

REAL_TOKEN = 'tok-super-secret-9f3a'
REAL_TOKEN2 = 'chat-id-77123'
REAL_PASSWORD = 'hunter2-basic-auth'


def _seed(**over):
    ch = {
        'id':           'ch-test-1',
        'name':         'Ops Telegram',
        'kind':         'telegram',
        'enabled':      True,
        'url':          '',
        'token':        REAL_TOKEN,
        'token2':       REAL_TOKEN2,
        'username':     'ops',
        'password':     REAL_PASSWORD,
        'categories':   ['config'],
        'min_severity': 'info',
        'digest':       'immediate',
        'quiet_hours':  '',
        'break_through': False,
    }
    ch.update(over)
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=s['auth_enabled'],
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        notification_channels=[ch])
    return ch


def _stored():
    return settings_mod.load_settings()['notification_channels']


def _payload(**over):
    body = {'domains': ['example.com'], 'cert_resolver': 'letsencrypt',
            'traefik_api_url': 'http://traefik:8080'}
    body.update(over)
    return body


def test_get_settings_never_returns_a_channel_secret(client):
    _seed()
    r = client.get('/api/settings')
    assert r.status_code == 200
    raw = r.get_data(as_text=True)
    assert REAL_TOKEN not in raw
    assert REAL_TOKEN2 not in raw
    assert REAL_PASSWORD not in raw
    ch = r.get_json()['notification_channels'][0]
    assert ch['token'] == '***'
    assert ch['token2'] == '***'
    assert ch['password'] == '***'
    assert ch['name'] == 'Ops Telegram'


def test_unset_secret_reads_back_empty_not_masked(client):
    _seed(token2='', password='')
    ch = client.get('/api/settings').get_json()['notification_channels'][0]
    assert ch['token'] == '***'
    assert ch['token2'] == ''
    assert ch['password'] == ''


def test_get_then_post_round_trip_keeps_the_real_token(client):
    _seed()
    channels = client.get('/api/settings').get_json()['notification_channels']
    assert channels[0]['token'] == '***'
    r = post_json(client, '/api/settings', _payload(notification_channels=channels))
    assert r.status_code == 200
    stored = _stored()[0]
    assert stored['token'] == REAL_TOKEN
    assert stored['token2'] == REAL_TOKEN2
    assert stored['password'] == REAL_PASSWORD


def test_post_response_is_redacted_too(client):
    _seed()
    channels = client.get('/api/settings').get_json()['notification_channels']
    r = post_json(client, '/api/settings', _payload(notification_channels=channels))
    raw = r.get_data(as_text=True)
    assert REAL_TOKEN not in raw
    assert r.get_json()['settings']['notification_channels'][0]['token'] == '***'


def test_post_without_the_key_leaves_channels_untouched(client):
    _seed()
    r = post_json(client, '/api/settings', _payload())
    assert r.status_code == 200
    stored = _stored()
    assert len(stored) == 1
    assert stored[0]['id'] == 'ch-test-1'
    assert stored[0]['token'] == REAL_TOKEN


def test_a_real_new_token_still_overwrites(client):
    _seed()
    channels = client.get('/api/settings').get_json()['notification_channels']
    channels[0]['token'] = 'tok-rotated-b2'
    post_json(client, '/api/settings', _payload(notification_channels=channels))
    assert _stored()[0]['token'] == 'tok-rotated-b2'


def test_editing_a_channel_keeps_the_secret_it_did_not_touch(client):
    _seed()
    channels = client.get('/api/settings').get_json()['notification_channels']
    channels[0]['name'] = 'Renamed'
    channels[0]['min_severity'] = 'warning'
    post_json(client, '/api/settings', _payload(notification_channels=channels))
    stored = _stored()[0]
    assert stored['name'] == 'Renamed'
    assert stored['min_severity'] == 'warning'
    assert stored['token'] == REAL_TOKEN


def test_a_new_channel_with_the_sentinel_gets_no_borrowed_secret(client):
    _seed()
    post_json(client, '/api/settings', _payload(notification_channels=[{
        'id': 'ch-test-2', 'name': 'Alerts', 'kind': 'ntfy', 'enabled': True,
        'url': 'https://ntfy.sh/alerts', 'token': '***', 'token2': '',
        'username': '', 'password': '', 'categories': ['config'],
        'min_severity': 'info', 'digest': 'immediate', 'quiet_hours': '',
        'break_through': False,
    }]))
    stored = _stored()
    assert len(stored) == 1
    assert stored[0]['id'] == 'ch-test-2'
    assert stored[0]['token'] == ''


def test_an_explicit_empty_list_clears_channels(client):
    _seed()
    post_json(client, '/api/settings', _payload(notification_channels=[]))
    assert _stored() == []


def test_credential_bearing_url_is_masked(app_module):
    ch = {'kind': 'discord', 'url': 'https://discord.com/api/webhooks/123/SECRET',
          'token': '', 'token2': '', 'password': ''}
    out = app_module._redact_channel(ch)
    assert 'SECRET' not in str(out)
    assert out['url'] == 'https://discord.com/***'


def test_gotify_server_url_is_not_masked(app_module):
    ch = {'kind': 'gotify', 'url': 'https://push.example.com/gotify',
          'token': 'APPTOKEN', 'token2': '', 'password': ''}
    out = app_module._redact_channel(ch)
    assert out['url'] == 'https://push.example.com/gotify'
    assert out['token'] == '***'


def test_masked_url_round_trip_keeps_the_stored_url(app_module):
    merged = app_module._merge_channel_secrets(
        [{'id': 'a', 'kind': 'discord', 'url': 'https://discord.com/***', 'token': '***'}],
        [{'id': 'a', 'kind': 'discord',
          'url': 'https://discord.com/api/webhooks/123/SECRET', 'token': 'REAL'}])
    assert merged[0]['url'].endswith('SECRET')
    assert merged[0]['token'] == 'REAL'


def test_a_genuine_new_url_still_overwrites(app_module):
    merged = app_module._merge_channel_secrets(
        [{'id': 'a', 'kind': 'discord', 'url': 'https://discord.com/api/webhooks/9/NEW'}],
        [{'id': 'a', 'kind': 'discord', 'url': 'https://old'}])
    assert merged[0]['url'].endswith('NEW')
