import core.settings as settings_mod


def _enable_oidc():
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=True,
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        setup_complete=True, oidc_enabled=True,
        oidc_provider_url='https://idp.example.com',
        oidc_client_id='tm-client', oidc_client_secret='tm-secret',
    )


class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.text = payload, status, str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        pass


def _discovery(methods=None):
    cfg = {
        'authorization_endpoint': 'https://idp.example.com/authorize',
        'token_endpoint': 'https://idp.example.com/token',
        'userinfo_endpoint': 'https://idp.example.com/userinfo',
        # the stubbed GET serves this for userinfo too, so the callback can run to completion
        'email': 'someone@example.com',
    }
    if methods is not None:
        cfg['token_endpoint_auth_methods_supported'] = methods
    return lambda *a, **k: _Resp(cfg)


def _start(client, monkeypatch, methods=None):
    _enable_oidc()
    monkeypatch.setattr('app.requests.get', _discovery(methods))
    client.get('/auth/oidc/login')
    with client.session_transaction() as sess:
        return sess['oidc_state']


def test_basic_is_tried_first_when_discovery_is_silent(client, monkeypatch):
    """OIDC Core: an unregistered method defaults to client_secret_basic."""
    state = _start(client, monkeypatch, methods=None)
    calls = []

    def _post(url, data=None, auth=None, headers=None, **k):
        calls.append({'auth': auth, 'headers': headers or {},
                      'body_secret': (data or {}).get('client_secret')})
        return _Resp({'id_token': '', 'access_token': 'x'})

    monkeypatch.setattr('app.requests.post', _post)
    client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert len(calls) == 1
    hdr = calls[0]['headers'].get('Authorization', '')
    assert hdr.startswith('Basic '), 'should authenticate with HTTP Basic'
    import base64 as _b64
    assert _b64.b64decode(hdr.split()[1]).decode() == 'tm-client:tm-secret'
    assert calls[0]['body_secret'] is None, 'the secret must not also be in the body'


def test_post_is_used_when_basic_is_not_advertised(client, monkeypatch):
    state = _start(client, monkeypatch, methods=['client_secret_post'])
    calls = []

    def _post(url, data=None, auth=None, **k):
        calls.append({'auth': auth, 'body_secret': (data or {}).get('client_secret')})
        return _Resp({'id_token': '', 'access_token': 'x'})

    monkeypatch.setattr('app.requests.post', _post)
    client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert calls[0]['auth'] is None
    assert calls[0]['body_secret'] == 'tm-secret'


def test_the_code_is_never_sent_twice(client, monkeypatch):
    """The authorization code is single-use - a retry re-sends a spent code and the provider
    answers 'code has already been used', hiding the real error."""
    state = _start(client, monkeypatch, methods=None)
    calls = []

    def _post(url, data=None, auth=None, **k):
        calls.append('basic' if auth else 'post')
        return _Resp({'error': 'invalid_client'}, status=400)

    monkeypatch.setattr('app.requests.post', _post)
    client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert len(calls) == 1, f'the token endpoint must be called once, got {calls}'


def test_userinfo_failure_falls_back_to_the_id_token(client, monkeypatch):
    """Authelia puts email in the id_token, so an unreachable userinfo must not cost the login."""
    import base64, json
    _enable_oidc()
    st = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=st['domains'], cert_resolver=st['cert_resolver'],
        traefik_api_url=st['traefik_api_url'], auth_enabled=True,
        password_hash=st['password_hash'], visible_tabs=st['visible_tabs'],
        setup_complete=True, oidc_enabled=True,
        oidc_provider_url='https://idp.example.com',
        oidc_client_id='tm-client', oidc_client_secret='tm-secret',
        oidc_allow_any_authenticated=True)
    claims = {'email': 'someone@example.com', 'name': 'Someone', 'groups': ['admins']}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    id_token = f'header.{payload}.sig'

    monkeypatch.setattr('app.requests.get', _discovery(None))
    client.get('/auth/oidc/login')
    with client.session_transaction() as sess:
        state = sess['oidc_state']
        sess['oidc_nonce'] = ''

    monkeypatch.setattr('app.requests.post',
                        lambda *a, **k: _Resp({'id_token': id_token, 'access_token': 'tok'}))

    disc = _discovery(None)

    def _get(url, *a, **k):
        if 'userinfo' in url:
            raise OSError('userinfo unreachable')
        return disc(url, *a, **k)

    monkeypatch.setattr('app.requests.get', _get)
    r = client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert r.status_code == 302
    assert '/login' not in r.headers['Location'], \
        'login should succeed from the id_token claims when userinfo is unreachable'
