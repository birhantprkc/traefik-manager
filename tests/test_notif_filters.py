import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, 'scripts', 'test_notif_filters.mjs')


def test_the_filter_driver_ships_with_the_repo():
    assert os.path.isfile(DRIVER), (
        'scripts/test_notif_filters.mjs is the only executable coverage the '
        'notification category filter has: the counts, the hide-when-pointless '
        'rule, and clearing a filter whose category no longer exists')


def test_notification_category_filters_behave():
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed, run scripts/test_notif_filters.mjs where it is')
    proc = subprocess.run([node, DRIVER], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, (
        'the notification filter driver failed:\n%s\n%s' % (proc.stdout, proc.stderr))


def test_the_add_endpoint_honours_a_category(client):
    from conftest import post_json
    r = post_json(client, '/api/notifications/add',
                  {'type': 'info', 'message': 'ping sweep done', 'category': 'traefik'})
    assert r.status_code < 400, r.get_data(as_text=True)
    got = client.get('/api/notifications').get_json()
    rows = got if isinstance(got, list) else got.get('notifications', [])
    entry = next(n for n in rows if n['msg'] == 'ping sweep done')
    assert entry['category'] == 'traefik'


def test_an_unknown_category_falls_back_to_config(client):
    from conftest import post_json
    r = post_json(client, '/api/notifications/add',
                  {'type': 'info', 'message': 'odd one', 'category': 'not-a-category'})
    assert r.status_code < 400
    got = client.get('/api/notifications').get_json()
    rows = got if isinstance(got, list) else got.get('notifications', [])
    entry = next(n for n in rows if n['msg'] == 'odd one')
    assert entry['category'] == 'config'
