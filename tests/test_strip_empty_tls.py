from core.config import strip_empty_sections


def test_an_empty_tls_options_block_is_removed():
    cfg = {'http': {'routers': {'a': {}}}, 'tls': {'options': {}}}
    assert 'tls' not in strip_empty_sections(cfg)


def test_tls_survives_when_it_still_holds_a_profile():
    cfg = {'tls': {'options': {'modern': {'minVersion': 'VersionTLS13'}}}}
    out = strip_empty_sections(cfg)
    assert out['tls']['options']['modern']['minVersion'] == 'VersionTLS13'


def test_an_empty_certificates_list_is_removed_but_options_kept():
    cfg = {'tls': {'options': {'modern': {}}, 'certificates': []}}
    out = strip_empty_sections(cfg)
    assert 'certificates' not in out['tls']
    assert 'options' in out['tls']


def test_an_empty_servers_transports_block_is_removed():
    cfg = {'http': {'routers': {'a': {}}, 'serversTransports': {}}}
    out = strip_empty_sections(cfg)
    assert 'serversTransports' not in out['http']


def test_a_populated_servers_transports_block_survives():
    cfg = {'http': {'serversTransports': {'t': {'insecureSkipVerify': True}}}}
    out = strip_empty_sections(cfg)
    assert out['http']['serversTransports']['t']['insecureSkipVerify'] is True


def test_the_reporters_config_loads_after_stripping():
    cfg = {
        'http': {'routers': {'demo': {'rule': 'Host(`d.example.com`)', 'service': 'demo'}},
                 'services': {'demo': {'loadBalancer': {'servers': [{'url': 'http://10.0.0.9'}]}}}},
        'tls': {'options': {}},
    }
    out = strip_empty_sections(cfg)
    assert 'tls' not in out, 'an empty tls block makes Traefik reject the whole file'
    assert out['http']['routers']['demo']['service'] == 'demo'
