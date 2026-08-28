from core.routes_build import _build_apps, _server_field


TCP_BARE = {
    'tcp': {
        'routers': {'db': {'rule': 'HostSNI(`*`)', 'service': 'db-svc',
                           'entryPoints': ['postgres']}},
        'services': {'db-svc': {'loadBalancer': {'servers': ['10.0.0.5:5432']}}},
    }
}

HTTP_BARE = {
    'http': {
        'routers': {'web': {'rule': 'Host(`x.example.com`)', 'service': 'web-svc',
                            'entryPoints': ['websecure']}},
        'services': {'web-svc': {'loadBalancer': {'servers': ['http://10.0.0.6:80']}}},
    }
}


def test_a_bare_string_tcp_server_does_not_crash_the_tab():
    apps = _build_apps(TCP_BARE, config_file='agent.yml')
    assert len(apps) == 1, 'the route must still be listed'
    assert apps[0]['target'] == '10.0.0.5:5432'


def test_a_bare_string_http_server_does_not_crash_the_tab():
    apps = _build_apps(HTTP_BARE, config_file='agent.yml')
    assert len(apps) == 1
    assert apps[0]['target'] == 'http://10.0.0.6:80'


def test_one_bad_service_does_not_hide_the_good_ones():
    cfg = {'http': {
        'routers': {
            'good': {'rule': 'Host(`a`)', 'service': 'good-svc', 'entryPoints': ['websecure']},
            'bad':  {'rule': 'Host(`b`)', 'service': 'bad-svc',  'entryPoints': ['websecure']},
        },
        'services': {
            'good-svc': {'loadBalancer': {'servers': [{'url': 'http://10.0.0.1'}]}},
            'bad-svc':  {'loadBalancer': {'servers': ['http://10.0.0.2']}},
        },
    }}
    names = {a['name'] for a in _build_apps(cfg, config_file='agent.yml')}
    assert names == {'good', 'bad'}, names


def test_the_helper_handles_every_shape():
    assert _server_field([{'url': 'http://a'}], 'url') == 'http://a'
    assert _server_field(['http://a'], 'url') == 'http://a'
    assert _server_field([], 'url') == 'N/A'
    assert _server_field(None, 'url') == 'N/A'
    assert _server_field([''], 'url') == 'N/A'
    assert _server_field([123], 'url') == 'N/A'
    assert _server_field([{'address': '1.2.3.4:80'}], 'address') == '1.2.3.4:80'
