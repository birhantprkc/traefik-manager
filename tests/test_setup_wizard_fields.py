import core.settings as settings_mod


def _fresh_setup(client):
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=True,
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        setup_complete=False,
        crowdsec_lapi_url='', crowdsec_api_key='',
        crowdsec_machine_id='', crowdsec_machine_password='',
        git_backup_enabled=False, git_backup_repo='', git_backup_token='',
        git_backup_auto_push=False,
        webhook_url='', webhook_type='', notification_channels=[],
        geoip_enabled=False, default_theme='dark',
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


def test_setup_persists_crowdsec(client):
    _fresh_setup(client)
    client.post('/setup', data={**BASE,
                                'crowdsec_lapi_url': 'http://crowdsec:8080',
                                'crowdsec_api_key': 'bouncer-key',
                                'crowdsec_machine_id': 'tm',
                                'crowdsec_machine_password': 'pw'},
                headers={'X-Requested-With': 'fetch'})
    s = settings_mod.load_settings()
    assert s['crowdsec_lapi_url'] == 'http://crowdsec:8080'
    assert s['crowdsec_api_key'] == 'bouncer-key'
    assert s['crowdsec_machine_id'] == 'tm'


def test_setup_persists_git_backup(client):
    _fresh_setup(client)
    client.post('/setup', data={**BASE,
                                'git_backup_repo': 'https://github.com/you/cfg',
                                'git_backup_branch': 'main',
                                'git_backup_username': 'you',
                                'git_backup_token': 'ghp_x',
                                'git_backup_auto_push': 'on'},
                headers={'X-Requested-With': 'fetch'})
    s = settings_mod.load_settings()
    assert s['git_backup_enabled'] is True
    assert s['git_backup_repo'] == 'https://github.com/you/cfg'
    assert s['git_backup_auto_push'] is True


def test_setup_persists_a_notification_channel(client):
    _fresh_setup(client)
    client.post('/setup', data={**BASE,
                                'notify_kind': 'discord',
                                'notify_url': 'https://discord.com/api/webhooks/x'},
                headers={'X-Requested-With': 'fetch'})
    s = settings_mod.load_settings()
    channels = s['notification_channels']
    assert len(channels) == 1
    assert channels[0]['kind'] == 'discord'
    assert channels[0]['url'] == 'https://discord.com/api/webhooks/x'


def test_setup_persists_geoip_and_theme(client):
    _fresh_setup(client)
    client.post('/setup', data={**BASE,
                                'geoip_enabled': 'on',
                                'default_theme': 'light'},
                headers={'X-Requested-With': 'fetch'})
    s = settings_mod.load_settings()
    assert s['geoip_enabled'] is True
    assert s['default_theme'] == 'light'


def test_setup_rejects_a_bogus_theme(client):
    _fresh_setup(client)
    client.post('/setup', data={**BASE, 'default_theme': 'neon'},
                headers={'X-Requested-With': 'fetch'})
    assert settings_mod.load_settings()['default_theme'] == 'dark'


def test_skipping_the_optional_steps_leaves_them_unset(client):
    _fresh_setup(client)
    client.post('/setup', data=BASE, headers={'X-Requested-With': 'fetch'})
    s = settings_mod.load_settings()
    assert not s.get('crowdsec_lapi_url')
    assert not s.get('git_backup_enabled')
    assert not s.get('webhook_url')
    assert not s.get('notification_channels')
    assert not s.get('geoip_enabled')


def test_setup_test_endpoints_close_after_setup(client):
    _fresh_setup(client)
    client.post('/setup', data=BASE, headers={'X-Requested-With': 'fetch'})
    for path in ('/setup/test-crowdsec', '/setup/test-git'):
        r = client.post(path, json={}, headers={'X-CSRF-Token': 'testtoken'})
        assert r.status_code == 404, path
