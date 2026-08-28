import fcntl
import json
import os
import subprocess
import sys
import textwrap
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from core import crowdsec as cs

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORKER = textwrap.dedent("""
    import json, os, sys, time
    from core.crowdsec import cs_decisions_stream

    role, workdir, out, calls = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])

    def wait(name):
        for _ in range(1200):
            if os.path.exists(os.path.join(workdir, name)):
                return
            time.sleep(0.05)
        raise SystemExit('timeout waiting for ' + name)

    def signal(name):
        open(os.path.join(workdir, name), 'w').close()

    rounds = []
    for i in range(1, calls + 1):
        wait('go-%s%d' % (role, i))
        rows, mode = cs_decisions_stream()
        rounds.append({'mode': mode, 'values': sorted(r['value'] for r in rows)})
        with open(out, 'w') as f:
            json.dump(rounds, f)
        signal('done-%s%d' % (role, i))
""")


def _decision(did, value):
    return {'id': did, 'value': value, 'origin': 'crowdsec', 'type': 'ban',
            'scenario': 'test/bf', 'scope': 'Ip', 'duration': '4h'}


class _LapiHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != '/v1/decisions/stream':
            self.send_response(404)
            self.end_headers()
            return
        startup = parse_qs(parsed.query).get('startup', ['false'])[0] == 'true'
        state = self.server.state
        with state['lock']:
            state['polls'].append(self.path)
            rows = state['decisions'] if startup else state['decisions'][state['cursor']:]
            state['cursor'] = len(state['decisions'])
            body = json.dumps({'new': list(rows), 'deleted': []}).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def lapi():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _LapiHandler)
    server.state = {'lock': threading.Lock(), 'polls': [], 'cursor': 0,
                    'decisions': [_decision(1, '1.1.1.1')]}
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    server.state['url'] = 'http://127.0.0.1:%d' % server.server_address[1]
    yield server.state
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def _worker_env(workdir, lapi, fresh):
    env = dict(os.environ)
    for var in ('CROWDSEC_MACHINE_ID', 'CROWDSEC_MACHINE_PASSWORD', 'CROWDSEC_CLIENT_CERT',
                'CROWDSEC_CLIENT_KEY', 'CROWDSEC_CA_CERT'):
        env.pop(var, None)
    env.update({
        'PYTHONPATH': REPO,
        'SETTINGS_PATH': os.path.join(workdir, 'manager.yml'),
        'CONFIG_PATH': os.path.join(workdir, 'dynamic.yml'),
        'BACKUP_DIR': os.path.join(workdir, 'backups'),
        'CROWDSEC_LAPI_URL': lapi['url'],
        'CROWDSEC_API_KEY': 'bouncer-key',
        'CROWDSEC_STREAM_FRESH_SECONDS': str(fresh),
    })
    return env


class _Workers:
    def __init__(self, tmp_path, lapi, fresh, calls):
        self.dir = str(tmp_path)
        script = os.path.join(self.dir, 'worker.py')
        with open(script, 'w') as f:
            f.write(WORKER)
        self.out = {}
        self.procs = {}
        for role in ('a', 'b'):
            self.out[role] = os.path.join(self.dir, 'out-%s.json' % role)
            self.procs[role] = subprocess.Popen(
                [sys.executable, script, role, self.dir, self.out[role], str(calls)],
                env=_worker_env(self.dir, lapi, fresh), cwd=REPO)

    def turn(self, role, index):
        open(os.path.join(self.dir, 'go-%s%d' % (role, index)), 'w').close()
        done = os.path.join(self.dir, 'done-%s%d' % (role, index))
        proc = self.procs[role]
        for _ in range(1200):
            if os.path.exists(done):
                return json.load(open(self.out[role]))[index - 1]
            if proc.poll() not in (None, 0):
                raise AssertionError('worker %s exited with %s' % (role, proc.returncode))
            time.sleep(0.05)
        raise AssertionError('worker %s never finished call %d' % (role, index))

    def finish(self):
        for role, proc in self.procs.items():
            assert proc.wait(timeout=30) == 0, 'worker %s failed' % role


def test_a_peers_fresh_poll_is_reused_instead_of_polling_again(tmp_path, lapi):
    workers = _Workers(tmp_path, lapi, fresh=30, calls=1)
    first = workers.turn('a', 1)
    lapi['decisions'].append(_decision(2, '2.2.2.2'))
    second = workers.turn('b', 1)
    workers.finish()

    assert first['values'] == ['1.1.1.1']
    assert second['values'] == first['values'], 'workers disagree about the active decisions'
    assert len(lapi['polls']) == 1, 'the LAPI was polled once per worker: %s' % lapi['polls']


def test_a_delta_consumed_by_one_worker_is_visible_to_the_other(tmp_path, lapi):
    workers = _Workers(tmp_path, lapi, fresh=0, calls=2)
    assert workers.turn('a', 1)['values'] == ['1.1.1.1']
    assert workers.turn('b', 1)['values'] == ['1.1.1.1']

    lapi['decisions'].append(_decision(2, '2.2.2.2'))
    after_a = workers.turn('a', 2)
    after_b = workers.turn('b', 2)
    workers.finish()

    assert after_a['values'] == ['1.1.1.1', '2.2.2.2']
    assert after_b['values'] == after_a['values'], 'the worker that lost the delta race went blind'


def test_a_stale_fingerprint_still_forces_a_full_resync(tmp_path, lapi):
    workers = _Workers(tmp_path, lapi, fresh=0, calls=1)
    assert workers.turn('a', 1)['mode'] == 'full'
    workers.turn('b', 1)
    workers.finish()

    lapi['decisions'].append(_decision(2, '2.2.2.2'))
    env = _worker_env(str(tmp_path), lapi, 30)
    env['CROWDSEC_API_KEY'] = 'rotated-key'
    script = os.path.join(str(tmp_path), 'worker.py')
    out = os.path.join(str(tmp_path), 'out-c.json')
    open(os.path.join(str(tmp_path), 'go-c1'), 'w').close()
    proc = subprocess.Popen([sys.executable, script, 'c', str(tmp_path), out, '1'],
                            env=env, cwd=REPO)
    assert proc.wait(timeout=30) == 0
    rounds = json.load(open(out))
    assert rounds[0]['mode'] == 'full'
    assert rounds[0]['values'] == ['1.1.1.1', '2.2.2.2']
    assert any('startup=true' in p for p in lapi['polls'][1:])


def test_a_locked_cache_serves_the_last_known_data_instead_of_double_polling(monkeypatch):
    monkeypatch.setenv('CROWDSEC_LAPI_URL', 'http://lapi.invalid:8080')
    monkeypatch.setenv('CROWDSEC_API_KEY', 'bouncer-key')
    monkeypatch.setenv('CROWDSEC_STREAM_FRESH_SECONDS', '0')
    cs.cs_stream_reset()
    polls = []

    def fake(method, path, **kw):
        polls.append(path)
        return {'new': [_decision(1, '1.1.1.1')], 'deleted': []}

    monkeypatch.setattr(cs, '_cs_request_strict', fake)
    assert cs.cs_decisions_stream()[1] == 'full'

    holder = open(cs._cs_stream_lock_path(), 'a+')
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
    try:
        rows, mode = cs.cs_decisions_stream()
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        holder.close()
        cs.cs_stream_reset()

    assert mode == 'cache'
    assert [r['value'] for r in rows] == ['1.1.1.1']
    assert len(polls) == 1, 'the LAPI was polled while another worker held the lock'
