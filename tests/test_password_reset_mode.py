import core.settings as settings_mod


def _reset_state(client):
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=True,
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        setup_complete=True, setup_password_reset=True,
        must_change_password=True,
    )


def test_reset_mode_shows_only_the_password_form(client):
    _reset_state(client)
    r = client.get('/setup')
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'Set a new password' in body
    assert 'id="panel-0"' not in body, 'the wizard panels must not render in reset mode'
    assert 'id="wzb-0"' not in body, 'the wizard step sidebar must not render in reset mode'
    assert 'Choose your views' not in body


def test_reset_sets_the_password_and_clears_the_flag(client):
    _reset_state(client)
    r = client.post('/setup', data={'csrf_token': 'testtoken',
                                    'password': 'a-brand-new-password',
                                    'confirm': 'a-brand-new-password'})
    assert r.status_code == 302
    s = settings_mod.load_settings()
    assert s['setup_password_reset'] is False
    assert s['must_change_password'] is False
    assert s['setup_complete'] is True, 'reset must not disturb setup_complete'


def test_reset_rejects_a_short_password(client):
    _reset_state(client)
    r = client.post('/setup', data={'csrf_token': 'testtoken',
                                    'password': 'short', 'confirm': 'short'})
    assert 'at least 8 characters' in r.get_data(as_text=True)
    assert settings_mod.load_settings()['setup_password_reset'] is True


def test_reset_rejects_a_mismatch(client):
    _reset_state(client)
    r = client.post('/setup', data={'csrf_token': 'testtoken',
                                    'password': 'a-brand-new-password',
                                    'confirm': 'something-else-entirely'})
    assert 'do not match' in r.get_data(as_text=True)
    assert settings_mod.load_settings()['setup_password_reset'] is True


def test_setup_is_untouched_when_the_flag_is_off(client):
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=True,
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        setup_complete=True, setup_password_reset=False,
        must_change_password=False,
    )
    r = client.get('/setup')
    assert r.status_code == 302, 'completed setup should still redirect away'
