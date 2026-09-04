import core.auth as auth


def _probe(client_factory, auth_on, oidc_on, monkeypatch):
    monkeypatch.setattr(auth, '_auth_enabled', lambda: auth_on)
    monkeypatch.setattr(auth, '_oidc_active', lambda: oidc_on)
    return client_factory().get('/api/routes').status_code


def test_the_api_needs_a_key_when_the_password_is_enabled(anon_client, app_module, monkeypatch):
    monkeypatch.setattr(auth, '_auth_enabled', lambda: True)
    monkeypatch.setattr(auth, '_oidc_active', lambda: False)
    assert anon_client.get('/api/routes').status_code == 401


def test_the_api_needs_a_key_when_only_oidc_is_enabled(anon_client, monkeypatch):
    monkeypatch.setattr(auth, '_auth_enabled', lambda: False)
    monkeypatch.setattr(auth, '_oidc_active', lambda: True)
    assert anon_client.get('/api/routes').status_code == 401, (
        'disabling the password form must not open the api when oidc is the login method')


def test_the_api_is_open_only_when_both_are_disabled(anon_client, monkeypatch):
    monkeypatch.setattr(auth, '_auth_enabled', lambda: False)
    monkeypatch.setattr(auth, '_oidc_active', lambda: False)
    assert anon_client.get('/api/routes').status_code == 200, (
        'this is the documented open case, and the docs must keep matching it')


def test_the_mobile_docs_describe_the_real_behaviour():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, 'docs', 'mobile.md'), encoding='utf-8') as fh:
        doc = fh.read()
    assert 'Without built-in auth, the `/api/*` route has no protection' not in doc, \
        'that is false whenever oidc is the login method'
    assert 'accepted in every mode' in doc
