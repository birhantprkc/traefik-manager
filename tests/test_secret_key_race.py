"""Concurrent workers must agree on the session signing key.

gunicorn runs 2 workers and _load_or_create_secret_key() executes at import in
each. On a fresh config directory both used to see no .secret_key, both
generated one, and the second overwrote the first - so each worker signed
sessions with a different key and roughly half of all requests came back
"Session expired - please refresh the page." until a restart.
"""
import os
import subprocess
import time
import sys
import textwrap

CHILD = textwrap.dedent('''
    import os, sys, time, secrets

    _SECRET_KEY_PATH = sys.argv[1]
    _GATE = sys.argv[2]

    while not os.path.exists(_GATE):
        time.sleep(0.002)

    def load_or_create():
        if os.path.exists(_SECRET_KEY_PATH):
            key = open(_SECRET_KEY_PATH, 'rb').read().strip()
            if len(key) >= 32:
                return key
        key = secrets.token_hex(32).encode()
        key_dir = os.path.dirname(_SECRET_KEY_PATH)
        os.makedirs(key_dir, exist_ok=True)
        tmp = os.path.join(key_dir, '.secret_key.%d.tmp' % os.getpid())
        with open(tmp, 'wb') as f:
            f.write(key)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        try:
            os.link(tmp, _SECRET_KEY_PATH)
        except FileExistsError:
            existing = open(_SECRET_KEY_PATH, 'rb').read().strip()
            if len(existing) >= 32:
                key = existing
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        return key

    sys.stdout.write(load_or_create().decode())
''')


def _race(tmp_path, workers=16):
    script = tmp_path / 'child.py'
    script.write_text(CHILD)
    target = str(tmp_path / 'cfg' / '.secret_key')
    gate = tmp_path / 'gate'
    procs = [subprocess.Popen([sys.executable, str(script), target, str(gate)],
                              stdout=subprocess.PIPE, text=True)
             for _ in range(workers)]
    time.sleep(0.35)          # let every child reach the gate before opening it
    gate.write_text('go')
    out = [p.communicate()[0] for p in procs]
    gate.unlink()
    return out, target


def test_every_worker_ends_up_with_the_same_key(tmp_path):
    keys, target = _race(tmp_path)
    assert len(set(keys)) == 1, (
        'workers disagreed on the signing key, so sessions minted by one are '
        'rejected by another: %r' % sorted(set(k[:12] for k in keys)))
    assert len(keys[0]) >= 32


def test_the_key_each_worker_holds_is_the_one_on_disk(tmp_path):
    keys, target = _race(tmp_path)
    on_disk = open(target, 'rb').read().strip().decode()
    assert keys[0] == on_disk, 'the in-memory key must match the persisted one'


def test_the_key_file_is_not_world_readable(tmp_path):
    _keys, target = _race(tmp_path, workers=2)
    assert oct(os.stat(target).st_mode & 0o777) == '0o600'


def test_an_existing_key_is_reused_rather_than_replaced(tmp_path):
    keys, target = _race(tmp_path, workers=2)
    first = keys[0]
    again, _ = _race(tmp_path, workers=4)
    assert set(again) == {first}, 'a later start must not mint a new key'
