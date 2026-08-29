import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def test_a_failed_route_load_clears_what_is_on_screen():
    js = _read('static', 'js', 'routes.js')
    body = js.split('async function refreshRoutes', 1)[1].split('\n}\n', 1)[0]
    assert '_clearRouteViews' in body
    assert 'showToast(await _errText(res' not in body, (
        'returning after only a toast leaves the previous server rendered, so an offline '
        'agent shows the Host route list')


def test_the_clear_empties_both_grids_and_the_service_cache():
    js = _read('static', 'js', 'routes.js')
    body = js.split('function _clearRouteViews', 1)[1].split('\n}\n', 1)[0]
    assert 'renderRouteGrid([])' in body
    assert 'renderMwGrid([])' in body
    assert '_tmServices = null' in body


def test_the_empty_state_names_the_server_it_is_empty_for():
    js = _read('static', 'js', 'routes.js')
    body = js.split('function _clearRouteViews', 1)[1].split('\n}\n', 1)[0]
    assert '_activeAgent' in body and 'name' in body, \
        'the banner should say which server has no data, not just that something failed'


def test_switching_servers_empties_the_grid_first():
    html = _read('templates', 'index.html')
    body = html.split('function switchServer', 1)[1].split('\n}', 1)[0]
    assert 'renderRouteGrid([])' in body, (
        'without this the previous server stays on screen until the new load returns, '
        'and forever if it fails')
