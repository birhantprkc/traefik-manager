from core import crowdsec as C


def _alert(ip, scenario, events, cn=None, asn=None, as_name=None):
    src = {'value': ip}
    if cn:
        src['cn'] = cn
    if asn:
        src['as_number'] = asn
    if as_name:
        src['as_name'] = as_name
    return {'id': 1, 'scenario': 'crowdsecurity/' + scenario,
            'events_count': events, 'source': src,
            'decisions': [{'origin': 'crowdsec'}]}


def test_a_single_source_is_named_with_country_and_network():
    msg = C.summarise_alerts([_alert('80.94.95.211', 'http-probing', 21,
                                     'DE', '24940', 'Hetzner')], '10 minutes')
    assert '80.94.95.211' in msg
    assert '\U0001F1E9\U0001F1EA' in msg and 'AS24940 Hetzner' in msg
    assert '21 events' in msg


def test_missing_geoip_enrichment_degrades_cleanly():
    msg = C.summarise_alerts([_alert('80.94.95.211', 'http-probing', 21)], '10 minutes')
    assert '80.94.95.211' in msg
    assert '(' not in msg


def test_scenarios_are_listed_not_just_the_worst():
    msg = C.summarise_alerts([_alert('1.1.1.1', 'http-probing', 5),
                              _alert('1.1.1.1', 'http-sqli-probing', 2)], '10 minutes')
    assert 'http-probing' in msg and 'http-sqli-probing' in msg


def test_the_scenario_list_is_capped():
    msg = C.summarise_alerts([_alert('1.1.1.1', f'scen-{i}', 1) for i in range(9)], '1 hour')
    assert 'and 5 more' in msg
    assert 'scen-8' not in msg


def test_many_sources_still_collapse_to_one_message():
    msg = C.summarise_alerts([_alert('1.2.3.4', 'http-probing', 42, 'RU', '9009', 'M247'),
                              _alert('5.6.7.8', 'http-bad-user-agent', 8),
                              _alert('9.9.9.9', 'http-sqli-probing', 3)], '10 minutes')
    assert msg.count('\n') == 0
    assert '3 sources' in msg
    assert '53 events' in msg
    assert 'Worst: 1.2.3.4' in msg


def test_an_empty_window_says_nothing():
    assert C.summarise_alerts([], '10 minutes') == ''


def test_an_alert_with_no_source_does_not_crash():
    assert C.summarise_alerts([{'scenario': 'x', 'events_count': 1}], '10 minutes') == ''


def test_the_country_renders_as_a_flag():
    msg = C.summarise_alerts([_alert('1.2.3.4', 'http-probing', 5, 'DE')], '10 minutes')
    assert '\U0001F1E9\U0001F1EA' in msg, msg
    assert ', DE' not in msg, 'the flag replaces the code, it does not duplicate it'


def test_the_flag_matches_the_javascript_helper():
    assert C._cs_flag('de') == '\U0001F1E9\U0001F1EA'
    assert C._cs_flag('US') == '\U0001F1FA\U0001F1F8'


def test_a_junk_country_code_falls_back_to_the_raw_value():
    for bad in ('', 'X', 'XXX', '1A', None):
        assert C._cs_flag(bad) == ''
    msg = C.summarise_alerts([_alert('1.2.3.4', 'http-probing', 5, 'ZZZ')], '10 minutes')
    assert 'ZZZ' in msg, 'an unmappable code should still be shown'
