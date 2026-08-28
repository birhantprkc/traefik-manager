import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, 'scripts', 'test_toast_category.mjs')


def test_the_driver_ships_with_the_repo():
    assert os.path.isfile(DRIVER), (
        'scripts/test_toast_category.mjs is the only coverage for how a toast picks '
        'its notification category; without it every toast silently files under config')


def test_toast_category_inference():
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed, run scripts/test_toast_category.mjs where it is')
    proc = subprocess.run([node, DRIVER], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, (
        'the toast category driver failed:\n%s\n%s' % (proc.stdout, proc.stderr))


def test_the_log_endpoint_honours_a_category(client):
    from conftest import post_json
    r = post_json(client, '/api/notifications/log',
                  {'type': 'success', 'message': 'agent removed', 'category': 'agent'})
    assert r.status_code < 400, r.get_data(as_text=True)
    got = client.get('/api/notifications').get_json()
    rows = got if isinstance(got, list) else got.get('notifications', [])
    assert next(n for n in rows if n['msg'] == 'agent removed')['category'] == 'agent'


def test_the_log_endpoint_rejects_an_unknown_category(client):
    from conftest import post_json
    r = post_json(client, '/api/notifications/log',
                  {'type': 'success', 'message': 'odd log', 'category': 'nope'})
    assert r.status_code < 400
    got = client.get('/api/notifications').get_json()
    rows = got if isinstance(got, list) else got.get('notifications', [])
    assert next(n for n in rows if n['msg'] == 'odd log')['category'] == 'config'
