import base64
import hashlib
import re
from urllib.parse import parse_qs, urlparse

import core.settings as settings_mod


def _enable_oidc(monkeypatch):
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=True,
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        setup_complete=True,
        oidc_enabled=True,
        oidc_provider_url='https://idp.example.com',
        oidc_client_id='tm-client',
        oidc_client_secret='tm-secret',
    )


class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.text = payload, status, str(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise AssertionError('should not be called for 4xx in the new code path')


def test_authorize_request_carries_a_s256_challenge(client, monkeypatch):
    _enable_oidc(monkeypatch)
    monkeypatch.setattr('app.requests.get', lambda *a, **k: _Resp({
        'authorization_endpoint': 'https://idp.example.com/authorize',
        'token_endpoint': 'https://idp.example.com/token',
    }))
    r = client.get('/auth/oidc/login')
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers['Location']).query)
    assert q['code_challenge_method'] == ['S256']
    challenge = q['code_challenge'][0]
    assert '=' not in challenge, 'the challenge must be unpadded base64url'
    assert re.fullmatch(r'[A-Za-z0-9_-]+', challenge)

    with client.session_transaction() as sess:
        verifier = sess['oidc_verifier']
    expected = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode('ascii')).digest()).decode('ascii').rstrip('=')
    assert challenge == expected, 'challenge must be S256 of the stored verifier'


def test_token_exchange_sends_the_matching_verifier(client, monkeypatch):
    _enable_oidc(monkeypatch)
    monkeypatch.setattr('app.requests.get', lambda *a, **k: _Resp({
        'authorization_endpoint': 'https://idp.example.com/authorize',
        'token_endpoint': 'https://idp.example.com/token',
    }))
    client.get('/auth/oidc/login')
    with client.session_transaction() as sess:
        verifier, state = sess['oidc_verifier'], sess['oidc_state']

    sent = {}

    def _post(url, data=None, **k):
        sent.update(data or {})
        return _Resp({'error': 'invalid_client',
                      'error_description': 'mismatched secret'}, status=400)

    monkeypatch.setattr('app.requests.post', _post)
    client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert sent.get('code_verifier') == verifier


def test_provider_error_body_is_surfaced(client, monkeypatch, caplog):
    _enable_oidc(monkeypatch)
    monkeypatch.setattr('app.requests.get', lambda *a, **k: _Resp({
        'authorization_endpoint': 'https://idp.example.com/authorize',
        'token_endpoint': 'https://idp.example.com/token',
    }))
    client.get('/auth/oidc/login')
    with client.session_transaction() as sess:
        state = sess['oidc_state']

    monkeypatch.setattr('app.requests.post', lambda *a, **k: _Resp(
        {'error': 'invalid_client', 'error_description': 'Client secret mismatch'}, status=400))

    with caplog.at_level('ERROR'):
        r = client.get(f'/auth/oidc/callback?code=abc&state={state}')
    assert r.status_code == 302
    assert 'Client secret mismatch' in caplog.text, \
        'the provider error must reach the log, not be swallowed by raise_for_status'
