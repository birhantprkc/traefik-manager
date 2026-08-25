import core.settings as settings_mod
from conftest import post_json

TOO_LONG = 'e' * 73
AT_LIMIT = 'e' * 72
ACCENTED = 'é' * 40


def _save(**over):
    s = settings_mod.load_settings()
    base = dict(domains=s['domains'], cert_resolver=s['cert_resolver'],
                traefik_api_url=s['traefik_api_url'], auth_enabled=True,
                password_hash=s['password_hash'], visible_tabs=s['visible_tabs'])
    base.update(over)
    settings_mod.save_settings(**base)


def _reset_state():
    _save(setup_complete=True, setup_password_reset=True, must_change_password=True)


def _fresh_setup():
    _save(setup_complete=False, crowdsec_lapi_url='', crowdsec_api_key='',
          crowdsec_machine_id='', crowdsec_machine_password='',
          git_backup_enabled=False, git_backup_repo='', git_backup_token='',
          git_backup_auto_push=False, webhook_url='', webhook_type='',
          notification_channels=[], geoip_enabled=False, default_theme='dark')


WIZARD = {
    'csrf_token': 'testtoken',
    'domains': 'example.com',
    'cert_resolver': 'letsencrypt',
    'traefik_api_url': 'http://traefik:8080',
    'visible_tabs': '{}',
}


def test_reset_mode_rejects_a_password_over_the_bcrypt_limit(client):
    _reset_state()
    r = client.post('/setup', data={'csrf_token': 'testtoken',
                                    'password': TOO_LONG, 'confirm': TOO_LONG})
    assert r.status_code == 200
    assert '72 bytes' in r.get_data(as_text=True)
    assert settings_mod.load_settings()['setup_password_reset'] is True


def test_reset_mode_rejects_accented_text_that_is_short_enough_to_look_valid(client):
    """40 accented characters clear the 8 character rule but are 80 bytes to bcrypt."""
    _reset_state()
    r = client.post('/setup', data={'csrf_token': 'testtoken',
                                    'password': ACCENTED, 'confirm': ACCENTED})
    assert r.status_code == 200
    assert '72 bytes' in r.get_data(as_text=True)
    assert settings_mod.load_settings()['setup_password_reset'] is True


def test_initial_setup_rejects_a_password_over_the_bcrypt_limit(client):
    _fresh_setup()
    r = client.post('/setup', data={**WIZARD, 'password': TOO_LONG, 'confirm': TOO_LONG},
                    headers={'X-Requested-With': 'fetch'})
    assert r.status_code == 200
    assert '72 bytes' in r.get_data(as_text=True)
    assert settings_mod.load_settings()['setup_complete'] is False


def test_forced_change_rejects_a_password_over_the_bcrypt_limit(client):
    _save(must_change_password=True)
    r = client.post('/force-change-password',
                    data={'csrf_token': 'testtoken',
                          'new_password': TOO_LONG, 'confirm_password': TOO_LONG})
    assert r.status_code == 200
    assert '72 bytes' in r.get_data(as_text=True)
    assert settings_mod.load_settings()['must_change_password'] is True


def test_api_change_password_rejects_a_password_over_the_bcrypt_limit(client, app_module):
    _save(password_hash=app_module._hash_password('known-current-pw'),
          must_change_password=False)
    r = post_json(client, '/api/auth/change-password',
                  {'current_password': 'known-current-pw',
                   'new_password': TOO_LONG, 'confirm_password': TOO_LONG})
    assert r.status_code == 400, 'an over-long password must not reach bcrypt and 500'
    assert '72 bytes' in r.get_json()['error']


def test_api_change_password_accepts_a_password_at_exactly_the_limit(client, app_module):
    _save(password_hash=app_module._hash_password('known-current-pw'),
          must_change_password=False)
    r = post_json(client, '/api/auth/change-password',
                  {'current_password': 'known-current-pw',
                   'new_password': AT_LIMIT, 'confirm_password': AT_LIMIT})
    assert r.status_code == 200
    assert app_module._check_password(AT_LIMIT, settings_mod.load_settings()['password_hash'])
