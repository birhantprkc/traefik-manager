import core.notify_providers as providers
import core.settings as settings_mod
from core import env


def _fresh_setup():
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=True,
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        setup_complete=False,
        notification_channels=[],
        webhook_url='', webhook_type='',
    )


BASE = {
    'csrf_token': 'testtoken',
    'domains': 'example.com',
    'cert_resolver': 'letsencrypt',
    'traefik_api_url': 'http://traefik:8080',
    'visible_tabs': '{}',
    'password': 'averysafepassword',
    'confirm': 'averysafepassword',
}


def _post(client, **fields):
    _fresh_setup()
    return client.post('/setup', data={**BASE, **fields},
                       headers={'X-Requested-With': 'fetch'})


def _channels():
    return settings_mod.load_settings().get('notification_channels', [])


def test_wizard_creates_a_usable_discord_channel(client):
    _post(client, notify_kind='discord',
          notify_url='https://discord.com/api/webhooks/1/abc')
    chans = _channels()
    assert len(chans) == 1
    ch = chans[0]
    assert ch['kind'] == 'discord'
    assert ch['url'] == 'https://discord.com/api/webhooks/1/abc'
    assert ch['id'].startswith('ch_')
    assert ch['enabled'] is True
    assert sorted(ch['categories']) == sorted(settings_mod.CHANNEL_CATEGORIES)
    assert ch['min_severity'] == 'info'
    assert ch['digest'] == 'immediate'
    assert providers.missing_fields(ch) == []


def test_wizard_creates_a_usable_telegram_channel(client):
    _post(client, notify_kind='telegram',
          notify_token='123456:BOTTOKEN', notify_token2='-1001234567890')
    chans = _channels()
    assert len(chans) == 1
    ch = chans[0]
    assert ch['kind'] == 'telegram'
    assert ch['token'] == '123456:BOTTOKEN'
    assert ch['token2'] == '-1001234567890'
    assert providers.missing_fields(ch) == []


def test_wizard_creates_a_usable_gotify_channel(client):
    _post(client, notify_kind='gotify',
          notify_url='https://gotify.example.com', notify_token='AppToken')
    ch = _channels()[0]
    assert ch['kind'] == 'gotify'
    assert ch['token'] == 'AppToken'
    assert providers.missing_fields(ch) == []
    assert providers.gotify_url(ch['url']) == 'https://gotify.example.com/message'


def test_wizard_secrets_are_encrypted_on_disk(client):
    _post(client, notify_kind='pushover',
          notify_token='apptoken', notify_token2='userkey')
    raw = open(env.SETTINGS_PATH).read()
    assert 'apptoken' not in raw
    assert 'userkey' not in raw
    ch = _channels()[0]
    assert (ch['token'], ch['token2']) == ('apptoken', 'userkey')


def test_incomplete_channel_is_not_saved(client):
    r = _post(client, notify_kind='pushover', notify_token='apptoken')
    assert _channels() == []
    assert not settings_mod.load_settings().get('setup_complete')
    assert b'Complete every notification field' in r.data


def test_unknown_kind_is_not_saved(client):
    r = _post(client, notify_kind='matrix', notify_url='https://matrix.example.com')
    assert _channels() == []
    assert not settings_mod.load_settings().get('setup_complete')
    assert b'Choose a notification destination' in r.data


def test_skipping_notifications_creates_no_channel(client):
    _post(client, notify_kind='discord')
    assert _channels() == []
    assert settings_mod.load_settings().get('setup_complete') is True
