import os
import subprocess
import sys
import textwrap

from ruamel.yaml import YAML as SafeYAML

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORKER = textwrap.dedent("""
    import sys, time
    from core.notifications import add_notification, _load_notifications
    _load_notifications()
    time.sleep(0.4)
    who = sys.argv[1]
    for i in range(3):
        add_notification("info", f"{who}-{i}", webhook=False)
        time.sleep(0.2)
""")


def test_concurrent_workers_do_not_clobber_each_other(tmp_path):
    script = tmp_path / "worker.py"
    script.write_text(WORKER)
    notif = tmp_path / "notifications.yml"

    env = dict(os.environ)
    env.update({
        'PYTHONPATH': REPO,
        'NOTIFICATIONS_PATH': str(notif),
        'SETTINGS_PATH': str(tmp_path / 'manager.yml'),
        'CONFIG_PATH': str(tmp_path / 'dynamic.yml'),
    })

    procs = [subprocess.Popen([sys.executable, str(script), who], env=env, cwd=REPO)
             for who in ('A', 'B')]
    for p in procs:
        assert p.wait(timeout=60) == 0

    with open(notif) as f:
        data = SafeYAML(typ='safe').load(f) or []
    entries = data.get('items', []) if isinstance(data, dict) else data
    msgs = {e['msg'] for e in entries}
    ids  = [e['id'] for e in entries]
    assert len(ids) == len(set(ids)), f'concurrent workers reused an id: {sorted(ids)}'
    expected = {f'{w}-{i}' for w in ('A', 'B') for i in range(3)}
    missing = expected - msgs
    assert not missing, f'lost notifications from a concurrent worker: {sorted(missing)}'
