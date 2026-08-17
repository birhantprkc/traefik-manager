import base64
from urllib.parse import unquote

import core.settings as settings_mod


def _enable(secret='tm-secret', groups=''):
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=True,
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        setup_complete=True,
        oidc_enabled=True,
        oidc_provider_url='https://idp.example.com',
        oidc_client_id='tm-client',
        oidc_client_secret=secret,
        oidc_allowed_groups=groups,
    )


class _Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code, self.text = payload, status, str(payload)

    def json(self):
        return self._p

    def raise_for_status(self):
        pass


def _discovery(**extra):
    base = {
        'authorization_endpoint': 'https://idp.example.com/authorize',
        'token_endpoint': 'https://idp.example.com/token',
        'userinfo_endpoint': 'https://idp.example.com/userinfo',
    }
    base.update(extra)
    return _Resp(base)


def _id_token(claims):
    import json
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip('=')
    return f'header.{body}.sig'


def _start(client, monkeypatch, disc=None):
    monkeypatch.setattr('app.requests.get', lambda *a, **k: disc or _discovery())
    client.get('/auth/oidc/login')
    with client.session_transaction() as sess:
        return sess['oidc_state'], sess['oidc_nonce']


def test_basic_credentials_are_form_encoded(client, monkeypatch):
    """RFC 6749 2.3.1: form-encode before base64. Authentik percent-decodes what it receives,
    so a raw secret containing % arrives corrupted and the exchange fails."""
    _enable(secret='se%2Fcret+w')
    state, nonce = _start(client, monkeypatch)

    seen = {}

    def _post(url, data=None, headers=None, **k):
        seen['headers'] = headers or {}
        return _Resp({'id_token': _id_token({'email': 'a@b.c', 'nonce': nonce})})

    monkeypatch.setattr('app.requests.post', _post)
    client.get(f'/auth/oidc/callback?code=abc&state={state}')

    hdr = seen['headers'].get('Authorization', '')
    assert hdr.startswith('Basic '), 'confidential client must authenticate'
    decoded = base64.b64decode(hdr.split()[1]).decode()
    cid, _, csec = decoded.partition(':')
    assert unquote(cid) == 'tm-client'
    assert unquote(csec) == 'se%2Fcret+w'


def test_public_client_sends_no_client_authentication(client, monkeypatch):
    """No secret means a public client. Sending an empty Basic header is what makes
    providers answer invalid_client."""
    _enable(secret='')
    state, nonce = _start(client, monkeypatch)

    seen = {}

    def _post(url, data=None, headers=None, **k):
        seen['headers'] = headers or {}
        seen['data'] = data or {}
        return _Resp({'id_token': _id_token({'email': 'a@b.c', 'nonce': nonce})})

    monkeypatch.setattr('app.requests.post', _post)
    client.get(f'/auth/oidc/callback?code=abc&state={state}')

    assert 'Authorization' not in seen['headers']
    assert seen['data'].get('client_id') == 'tm-client'
    assert 'client_secret' not in seen['data']
    assert seen['data'].get('code_verifier'), 'PKCE is what authenticates a public client'


def test_userinfo_is_skipped_when_the_id_token_already_has_the_claims(client, monkeypatch):
    """requests applies its timeout per resolved address, so an unreachable userinfo host can
    burn the whole gunicorn worker budget. Do not call it when the claims are in hand."""
    _enable()
    state, nonce = _start(client, monkeypatch)

    called = {'userinfo': 0}

    def _get(url, *a, **k):
        if 'userinfo' in url:
            called['userinfo'] += 1
            return _Resp({'email': 'from-userinfo@b.c'})
        return _discovery()

    monkeypatch.setattr('app.requests.get', _get)
    monkeypatch.setattr('app.requests.post', lambda *a, **k: _Resp(
        {'id_token': _id_token({'email': 'a@b.c', 'nonce': nonce}), 'access_token': 'tok'}))

    client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert called['userinfo'] == 0
