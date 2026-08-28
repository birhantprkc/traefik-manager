import json

import pytest

from tests.conftest import tm

HEADERS = {'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'}


def _send(client, method, path, payload=None):
    kwargs = {'headers': HEADERS}
    if payload is not None:
        body = dict(payload)
        body.setdefault('csrf_token', 'testtoken')
        kwargs['data'] = json.dumps(body)
        kwargs['content_type'] = 'application/json'
    return getattr(client, method)(path, **kwargs)


def _channels():
    return tm.load_settings().get('notification_channels', [])


@pytest.fixture(autouse=True)
def no_channels():
    s = tm.load_settings()
    tm._save_channels(s, [])
    yield


def _create(client, **fields):
    payload = {'kind': 'gotify', 'name': 'Phone', 'url': 'https://gotify.example.com',
               'token': 'app-token'}
    payload.update(fields)
    return _send(client, 'post', '/api/notifications/channels', payload)


def test_list_is_empty_to_start(client):
    r = client.get('/api/notifications/channels')
    assert r.status_code == 200
    assert r.get_json() == {'channels': []}


def test_create_generates_an_id_and_redacts_the_secret(client):
    r = _create(client)
    assert r.status_code == 200, r.data
    ch = r.get_json()['channel']
    assert ch['id'].startswith('ch_')
    assert ch['token'] == '***'
    assert ch['kind'] == 'gotify'
    assert ch['name'] == 'Phone'
    assert ch['url'] == 'https://gotify.example.com'


def test_create_applies_defaults(client):
    ch = _create(client).get_json()['channel']
    assert ch['enabled'] is True
    assert ch['min_severity'] == 'info'
    assert ch['digest'] == 'immediate'
    assert ch['quiet_hours'] == ''
    assert ch['break_through'] is False
    assert set(ch['categories']) == set(tm._settings.CHANNEL_CATEGORIES)


def test_create_without_a_name_falls_back_to_the_kind(client):
    ch = _create(client, name='').get_json()['channel']
    assert ch['name'] == 'Gotify'


def test_the_stored_secret_is_the_real_one_not_the_redaction(client):
    _create(client)
    stored = _channels()
    assert len(stored) == 1
    assert stored[0]['token'] == 'app-token'


def test_list_redacts_every_secret_slot(client):
    _send(client, 'post', '/api/notifications/channels',
          {'kind': 'ntfy', 'name': 'Push', 'url': 'https://ntfy.sh/tm',
           'username': 'user', 'password': 'pw'})
    ch = client.get('/api/notifications/channels').get_json()['channels'][0]
    assert ch['password'] == '***'
    assert ch['token'] == ''
    assert ch['token2'] == ''
    assert ch['username'] == 'user'


def test_create_rejects_an_unknown_kind(client):
    r = _create(client, kind='carrier-pigeon')
    assert r.status_code == 400
    assert 'kind' in r.get_json()['error']
    assert _channels() == []


def test_create_rejects_a_missing_kind(client):
    r = _send(client, 'post', '/api/notifications/channels', {'name': 'No kind'})
    assert r.status_code == 400
    assert _channels() == []


@pytest.mark.parametrize('field,value', [
    ('categories',   ['config', 'not-a-category']),
    ('categories',   'config'),
    ('min_severity', 'critical'),
    ('digest',       'weekly'),
    ('quiet_hours',  '25:00-07:00'),
    ('quiet_hours',  '7:00-08:00'),
    ('quiet_hours',  '23:00'),
    ('quiet_hours',  'nonsense'),
])
def test_create_rejects_bad_field_values(client, field, value):
    r = _create(client, **{field: value})
    assert r.status_code == 400, f'{field}={value!r} was accepted'
    assert field.split('_')[0] in r.get_json()['error']
    assert _channels() == []


def test_create_accepts_a_valid_quiet_window(client):
    ch = _create(client, quiet_hours='23:00-07:00').get_json()['channel']
    assert ch['quiet_hours'] == '23:00-07:00'


def test_create_accepts_an_empty_quiet_window(client):
    ch = _create(client, quiet_hours='').get_json()['channel']
    assert ch['quiet_hours'] == ''


def test_update_changes_only_what_is_sent(client):
    cid = _create(client).get_json()['channel']['id']
    r = _send(client, 'put', f'/api/notifications/channels/{cid}',
              {'min_severity': 'error', 'enabled': False})
    assert r.status_code == 200, r.data
    ch = r.get_json()['channel']
    assert ch['min_severity'] == 'error'
    assert ch['enabled'] is False
    assert ch['name'] == 'Phone'
    assert ch['url'] == 'https://gotify.example.com'


def test_redaction_round_trip_keeps_the_stored_secret(client):
    cid = _create(client).get_json()['channel']['id']
    listed = client.get('/api/notifications/channels').get_json()['channels'][0]
    assert listed['token'] == '***'
    r = _send(client, 'put', f'/api/notifications/channels/{cid}', listed)
    assert r.status_code == 200, r.data
    assert _channels()[0]['token'] == 'app-token'


def test_update_replaces_a_secret_when_a_real_value_is_sent(client):
    cid = _create(client).get_json()['channel']['id']
    _send(client, 'put', f'/api/notifications/channels/{cid}', {'token': 'rotated'})
    assert _channels()[0]['token'] == 'rotated'


def test_update_rejects_an_unknown_kind_without_saving(client):
    cid = _create(client).get_json()['channel']['id']
    r = _send(client, 'put', f'/api/notifications/channels/{cid}', {'kind': 'smoke-signal'})
    assert r.status_code == 400
    assert _channels()[0]['kind'] == 'gotify'


def test_update_rejects_a_malformed_quiet_window(client):
    cid = _create(client).get_json()['channel']['id']
    r = _send(client, 'put', f'/api/notifications/channels/{cid}', {'quiet_hours': '23-07'})
    assert r.status_code == 400
    assert 'quiet_hours' in r.get_json()['error']


def test_update_of_an_unknown_id_is_404(client):
    r = _send(client, 'put', '/api/notifications/channels/ch_missing', {'name': 'x'})
    assert r.status_code == 404


def test_delete_removes_the_channel(client):
    cid = _create(client).get_json()['channel']['id']
    r = _send(client, 'delete', f'/api/notifications/channels/{cid}')
    assert r.status_code == 200
    assert _channels() == []


def test_delete_of_an_unknown_id_is_404(client):
    r = _send(client, 'delete', '/api/notifications/channels/ch_missing')
    assert r.status_code == 404


def test_delete_leaves_the_other_channels_alone(client):
    keep = _create(client, name='Keep').get_json()['channel']['id']
    drop = _create(client, name='Drop').get_json()['channel']['id']
    _send(client, 'delete', f'/api/notifications/channels/{drop}')
    assert [c['id'] for c in _channels()] == [keep]


def test_saving_a_channel_does_not_wipe_the_other_settings(client):
    before = tm.load_settings()
    _create(client)
    after = tm.load_settings()
    for key in ('domains', 'cert_resolver', 'traefik_api_url', 'auth_enabled',
                'password_hash', 'visible_tabs'):
        assert after[key] == before[key], key


def test_test_endpoint_names_the_missing_field_without_sending(client, monkeypatch):
    cid = _create(client, token='').get_json()['channel']['id']
    calls = []
    monkeypatch.setitem(tm._notify_providers.SENDERS, 'gotify',
                        lambda *a: calls.append(a) or (True, ''))
    r = _send(client, 'post', f'/api/notifications/channels/{cid}/test')
    assert r.status_code == 400
    assert 'token' in r.get_json()['error']
    assert calls == []


def test_test_endpoint_delivers(client, monkeypatch):
    cid = _create(client).get_json()['channel']['id']
    calls = []
    monkeypatch.setitem(tm._notify_providers.SENDERS, 'gotify',
                        lambda *a: calls.append(a) or (True, '9500 messages remaining this month'))
    r = _send(client, 'post', f'/api/notifications/channels/{cid}/test')
    assert r.status_code == 200, r.data
    body = r.get_json()
    assert body['ok'] is True
    assert body['detail'] == '9500 messages remaining this month'
    assert len(calls) == 1
    assert calls[0][0]['token'] == 'app-token'


def test_test_endpoint_ignores_the_channel_filters(client, monkeypatch):
    cid = _create(client, enabled=False, min_severity='error',
                  quiet_hours='00:00-23:59', digest='daily').get_json()['channel']['id']
    calls = []
    monkeypatch.setitem(tm._notify_providers.SENDERS, 'gotify',
                        lambda *a: calls.append(a) or (True, ''))
    r = _send(client, 'post', f'/api/notifications/channels/{cid}/test')
    assert r.status_code == 200
    assert len(calls) == 1


def test_test_endpoint_reports_a_provider_failure(client, monkeypatch):
    cid = _create(client).get_json()['channel']['id']
    monkeypatch.setitem(tm._notify_providers.SENDERS, 'gotify',
                        lambda *a: (False, 'HTTP 401: unauthorized'))
    r = _send(client, 'post', f'/api/notifications/channels/{cid}/test')
    assert r.status_code == 200
    body = r.get_json()
    assert body['ok'] is False
    assert 'HTTP 401' in body['error']


def test_test_endpoint_of_an_unknown_id_is_404(client):
    r = _send(client, 'post', '/api/notifications/channels/ch_missing/test')
    assert r.status_code == 404


def test_anonymous_access_is_refused(anon_client):
    assert anon_client.get('/api/notifications/channels').status_code == 401
    assert anon_client.post('/api/notifications/channels',
                            json={'kind': 'slack'}).status_code in (401, 403)


@pytest.mark.parametrize('method,path', [
    ('post',   '/api/notifications/channels'),
    ('put',    '/api/notifications/channels/ch_1'),
    ('delete', '/api/notifications/channels/ch_1'),
    ('post',   '/api/notifications/channels/ch_1/test'),
])
def test_writes_without_a_csrf_token_are_rejected(client, method, path):
    r = getattr(client, method)(path, json={'kind': 'slack'})
    assert r.status_code == 403, path
