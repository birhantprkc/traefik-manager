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


def test_invalid_grant_is_not_retried(client, monkeypatch):
    state = _start(client, monkeypatch, methods=None)
    calls = []

    def _post(url, data=None, headers=None, **k):
        calls.append(1)
        return _Resp({'error': 'invalid_grant',
                      'error_description': 'authorization code has already been used'}, status=400)

    monkeypatch.setattr('app.requests.post', _post)
    client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert len(calls) == 1, f'a spent code must not be re-sent, got {len(calls)} attempts'


def test_invalid_client_retries_with_the_other_method(client, monkeypatch):
    state = _start(client, monkeypatch, methods=['client_secret_post', 'client_secret_basic'])
    attempts = []

    def _post(url, data=None, headers=None, **k):
        attempts.append('basic' if (headers or {}).get('Authorization') else 'body')
        if len(attempts) == 1:
            return _Resp({'error': 'invalid_client'}, status=400)
        return _Resp({'access_token': 'a', 'id_token': ''})

    monkeypatch.setattr('app.requests.post', _post)
    client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert attempts == ['basic', 'body'], attempts
