import time

from core import notifications as N


def _t(h, m):
    return time.mktime(time.struct_time((2026, 8, 21, h, m, 0, 0, 1, -1)))


def test_quiet_window_wraps_past_midnight():
    assert N._in_quiet_hours('23:00-07:00', _t(2, 0))
    assert not N._in_quiet_hours('23:00-07:00', _t(12, 0))


def test_quiet_window_same_day():
    assert N._in_quiet_hours('09:00-17:00', _t(12, 0))
    assert not N._in_quiet_hours('09:00-17:00', _t(8, 0))


def test_quiet_window_absent_or_malformed_is_never_quiet():
    for w in ('', 'nonsense', '25:00-99:00', '08:00-08:00'):
        assert not N._in_quiet_hours(w, _t(2, 0))


def test_channel_filters_on_category_and_severity():
    ch = {'enabled': True, 'categories': ['crowdsec'], 'min_severity': 'warning'}
    assert N._wants(ch, 'error', 'crowdsec')
    assert not N._wants(ch, 'info', 'crowdsec')
    assert not N._wants(ch, 'error', 'config')


def test_disabled_channel_wants_nothing():
    ch = {'enabled': False, 'categories': [], 'min_severity': 'info'}
    assert not N._wants(ch, 'error', 'config')


def test_report_collapses_a_category_to_one_line():
    items = [{'type': 'warning', 'msg': f'rollup {i}', 'ts': f'0{i}:00:00',
              'category': 'crowdsec'} for i in range(1, 4)]
    report = N.build_report(items)
    assert report.count('CrowdSec') == 1
    assert '3 events' in report


def test_report_latest_means_latest_not_worst():
    items = [
        {'type': 'error', 'msg': 'Traefik unreachable', 'ts': '02:14:00', 'category': 'traefik'},
        {'type': 'success', 'msg': 'Traefik reachable again', 'ts': '02:19:00', 'category': 'traefik'},
    ]
    assert 'reachable again' in N.build_report(items)


def test_report_names_the_dropped_overflow():
    items = [{'type': 'info', 'msg': 'x', 'ts': '01:00:00', 'category': 'config'}]
    assert 'and 340 more' in N.build_report(items, dropped=340)


def test_empty_queue_makes_no_report():
    assert N.build_report([]) == ''
