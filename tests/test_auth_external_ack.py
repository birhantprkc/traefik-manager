import pytest

from tests.conftest import post_json
from core import auth as auth_mod
from core import settings as settings_mod


def _save(**kw):
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=s['auth_enabled'],
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'], **kw)


@pytest.fixture(autouse=True)
def _reset():
    _save(auth_external_ack=False)
    yield
    _save(auth_external_ack=False)


def test_defaults_to_false():
    assert settings_mod.load_settings().get('auth_external_ack') is False


def test_roundtrip():
    _save(auth_external_ack=True)
    assert settings_mod.load_settings()['auth_external_ack'] is True
    _save(auth_external_ack=False)
    assert settings_mod.load_settings()['auth_external_ack'] is False


def test_survives_an_unrelated_save():
    _save(auth_external_ack=True)
    s = settings_mod.load_settings()
    settings_mod.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=s['auth_enabled'],
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'])
    assert settings_mod.load_settings()['auth_external_ack'] is True


def test_ack_never_grants_access(monkeypatch):
    monkeypatch.setattr(auth_mod, '_auth_enabled', lambda: True)
    monkeypatch.setattr(auth_mod, '_oidc_active', lambda: False)
    _save(auth_external_ack=True)
    assert auth_mod._auth_required() is True


def test_ack_does_not_make_auth_required_when_none(monkeypatch):
    monkeypatch.setattr(auth_mod, '_auth_enabled', lambda: False)
    monkeypatch.setattr(auth_mod, '_oidc_active', lambda: False)
    _save(auth_external_ack=True)
    assert auth_mod._auth_required() is False


def test_endpoint_refuses_ack_while_auth_is_active(monkeypatch, client):
    monkeypatch.setattr(auth_mod, '_auth_enabled', lambda: True)
    monkeypatch.setattr(auth_mod, '_oidc_active', lambda: False)
    resp = post_json(client, '/api/auth/external-ack', {'auth_external_ack': True})
    assert resp.status_code == 400
    assert settings_mod.load_settings()['auth_external_ack'] is False


def test_endpoint_sets_ack_when_no_auth(monkeypatch, client):
    monkeypatch.setattr(auth_mod, '_auth_enabled', lambda: False)
    monkeypatch.setattr(auth_mod, '_oidc_active', lambda: False)
    resp = post_json(client, '/api/auth/external-ack', {'auth_external_ack': True})
    assert resp.status_code == 200
    assert settings_mod.load_settings()['auth_external_ack'] is True


def test_endpoint_can_always_clear(monkeypatch, client):
    monkeypatch.setattr(auth_mod, '_auth_enabled', lambda: True)
    monkeypatch.setattr(auth_mod, '_oidc_active', lambda: False)
    _save(auth_external_ack=True)
    resp = post_json(client, '/api/auth/external-ack', {'auth_external_ack': False})
    assert resp.status_code == 200
    assert settings_mod.load_settings()['auth_external_ack'] is False


def test_endpoint_rejects_a_request_without_csrf(client):
    resp = client.post('/api/auth/external-ack', json={'auth_external_ack': True})
    assert resp.status_code in (400, 403)
    assert settings_mod.load_settings()['auth_external_ack'] is False


def test_endpoint_rejects_anonymous(anon_client):
    resp = post_json(anon_client, '/api/auth/external-ack', {'auth_external_ack': True})
    assert resp.status_code in (302, 401, 403)
