import pytest

from core import notify_providers as np


class _Resp:
    def __init__(self, status_code=200, headers=None, payload=None, text=''):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError('no json')
        return self._payload


class _Post:
    def __init__(self, resp=None):
        self.resp = resp or _Resp()
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append({'url': url, **kwargs})
        return self.resp

    @property
    def last(self):
        return self.calls[-1]


@pytest.fixture
def post(monkeypatch):
    p = _Post()
    monkeypatch.setattr(np.requests, 'post', p)
    return p


def _channel(kind, **over):
    c = {
        'id': 'ch_test', 'name': kind.title(), 'kind': kind, 'enabled': True,
        'url': '', 'token': '', 'token2': '', 'username': '', 'password': '',
        'categories': ['config'], 'min_severity': 'info',
        'digest': 'immediate', 'quiet_hours': '', 'break_through': False,
    }
    c.update(over)
    return c


TS = '2026-08-21 10:30:00'


def test_required_fields_per_kind():
    assert np.required_fields('discord') == ['url']
    assert np.required_fields('slack') == ['url']
    assert np.required_fields('ntfy') == ['url']
    assert np.required_fields('generic') == ['url']
    assert np.required_fields('gotify') == ['url', 'token']
    assert np.required_fields('pushover') == ['token', 'token2']
    assert np.required_fields('pushbullet') == ['token']
    assert np.required_fields('telegram') == ['token', 'token2']


def test_required_fields_unknown_kind_is_empty():
    assert np.required_fields('carrier-pigeon') == []
    assert np.required_fields(None) == []


def test_every_kind_has_a_sender():
    from core.settings import CHANNEL_KINDS
    assert set(np.SENDERS) == set(CHANNEL_KINDS)


def test_discord_embed_and_colour(post):
    ok, err = np.send(_channel('discord', url='https://discord.test/hook'), 'error', 'Backup', 'disk full', TS)
    assert (ok, err) == (True, '')
    call = post.last
    assert call['url'] == 'https://discord.test/hook'
    assert call['timeout'] == 5
    assert call['auth'] is None
    embed = call['json']['embeds'][0]
    assert embed['title'] == 'disk full'
    assert embed['color'] == 0xf85149
    assert embed['footer']['text'] == 'Traefik Manager - ' + TS


def test_discord_unknown_type_uses_info_colour(post):
    np.send(_channel('discord', url='https://d.test/h'), 'weird', 'T', 'm', TS)
    assert post.last['json']['embeds'][0]['color'] == 0x58a6ff


def test_slack_icon_map(post):
    np.send(_channel('slack', url='https://slack.test/hook'), 'success', 'T', 'restored', TS)
    assert post.last['json'] == {'text': ':white_check_mark: *Traefik Manager* - restored'}


def test_slack_unknown_type_uses_bell(post):
    np.send(_channel('slack', url='https://slack.test/hook'), 'weird', 'T', 'hi', TS)
    assert post.last['json']['text'].startswith(':bell: ')


def test_ntfy_headers_and_plain_body(post):
    np.send(_channel('ntfy', url='https://ntfy.test/topic'), 'warning', 'T', 'cert expiring', TS)
    call = post.last
    assert call['data'] == b'cert expiring'
    assert call['headers'] == {'X-Title': 'Traefik Manager', 'X-Priority': '4', 'X-Tags': 'warning'}
    assert 'json' not in call


def test_ntfy_info_priority_three(post):
    np.send(_channel('ntfy', url='https://ntfy.test/topic'), 'info', 'T', 'hi', TS)
    assert post.last['headers']['X-Priority'] == '3'


def test_generic_json_fallback(post):
    np.send(_channel('generic', url='https://hook.test/in'), 'info', 'T', 'hello', TS)
    assert post.last['json'] == {'event': 'info', 'message': 'hello', 'timestamp': TS}


def test_legacy_basic_auth_only_when_username_set(post):
    np.send(_channel('generic', url='https://hook.test/in', username='u', password='p'), 'info', 'T', 'm', TS)
    assert post.last['auth'] == ('u', 'p')
    np.send(_channel('generic', url='https://hook.test/in', password='p'), 'info', 'T', 'm', TS)
    assert post.last['auth'] is None


def test_gotify_url_headers_and_priority(post):
    ok, err = np.send(_channel('gotify', url='https://gotify.test', token='AppTok'), 'error', 'Backup', 'disk full', TS)
    assert (ok, err) == (True, '')
    call = post.last
    assert call['url'] == 'https://gotify.test/message'
    assert call['headers'] == {'X-Gotify-Key': 'AppTok'}
    assert call['json'] == {'title': 'Backup', 'message': 'disk full', 'priority': 8}
    assert call['timeout'] == 5


def test_gotify_preserves_subpath(post):
    np.send(_channel('gotify', url='https://host.test/gotify/', token='t'), 'info', 'T', 'm', TS)
    assert post.last['url'] == 'https://host.test/gotify/message'
    np.send(_channel('gotify', url='https://host.test/a/b', token='t'), 'info', 'T', 'm', TS)
    assert post.last['url'] == 'https://host.test/a/b/message'


def test_gotify_priority_map(post):
    for type_, expected in (('error', 8), ('warning', 5), ('info', 3), ('success', 3)):
        np.send(_channel('gotify', url='https://g.test', token='t'), type_, 'T', 'm', TS)
        assert post.last['json']['priority'] == expected


def test_pushover_form_body_carries_both_secrets(post):
    ok, err = np.send(_channel('pushover', token='apptok', token2='userkey'), 'error', 'Alert', 'down', TS)
    assert ok
    call = post.last
    assert call['url'] == 'https://api.pushover.net/1/messages.json'
    assert 'json' not in call
    assert call['data']['token'] == 'apptok'
    assert call['data']['user'] == 'userkey'
    assert call['data']['title'] == 'Alert'
    assert call['data']['message'] == 'down'
    assert call['data']['priority'] == 1
    assert call['timeout'] == 5


def test_pushover_non_error_priority_zero(post):
    np.send(_channel('pushover', token='a', token2='u'), 'warning', 'T', 'm', TS)
    assert post.last['data']['priority'] == 0


def test_pushover_truncates_title_and_message(post):
    np.send(_channel('pushover', token='a', token2='u'), 'info', 'T' * 400, 'm' * 5000, TS)
    data = post.last['data']
    assert len(data['title']) == 250
    assert len(data['message']) == 1024
    assert data['title'] == 'T' * 250


def test_pushover_priority_two_always_carries_retry_and_expire(post):
    np.send(_channel('pushover', token='a', token2='u', priority=2), 'error', 'T', 'm', TS)
    data = post.last['data']
    assert data['priority'] == 2
    assert data['retry'] == 60
    assert data['expire'] == 1800


def test_pushover_priority_clamped_and_no_retry_below_two(post):
    np.send(_channel('pushover', token='a', token2='u', priority=9), 'info', 'T', 'm', TS)
    assert post.last['data']['priority'] == 2
    assert post.last['data']['retry'] == 60
    np.send(_channel('pushover', token='a', token2='u', priority=1), 'info', 'T', 'm', TS)
    assert 'retry' not in post.last['data'] and 'expire' not in post.last['data']
    np.send(_channel('pushover', token='a', token2='u', priority=-9), 'info', 'T', 'm', TS)
    assert post.last['data']['priority'] == -2


def test_pushover_bad_priority_falls_back_to_type(post):
    np.send(_channel('pushover', token='a', token2='u', priority='nonsense'), 'error', 'T', 'm', TS)
    assert post.last['data']['priority'] == 1


def test_pushover_never_sends_html_and_monospace_together(post):
    np.send(_channel('pushover', token='a', token2='u', html=True, monospace=True), 'info', 'T', 'm', TS)
    data = post.last['data']
    assert data.get('html') == 1
    assert 'monospace' not in data
    np.send(_channel('pushover', token='a', token2='u', monospace=True), 'info', 'T', 'm', TS)
    assert post.last['data'].get('monospace') == 1
    assert 'html' not in post.last['data']


def test_pushover_returns_remaining_allowance(monkeypatch):
    p = _Post(_Resp(headers={'X-Limit-App-Remaining': '9873'}))
    monkeypatch.setattr(np.requests, 'post', p)
    ok, msg = np.send(_channel('pushover', token='a', token2='u'), 'info', 'T', 'm', TS)
    assert ok
    assert '9873' in msg


def test_pushover_errors_are_joined(monkeypatch):
    p = _Post(_Resp(status_code=400, payload={'status': 0, 'errors': ['user identifier is invalid', 'nope']}))
    monkeypatch.setattr(np.requests, 'post', p)
    ok, err = np.send(_channel('pushover', token='a', token2='u'), 'info', 'T', 'm', TS)
    assert not ok
    assert err == 'user identifier is invalid; nope'


def test_pushbullet_header_and_body(post):
    ok, err = np.send(_channel('pushbullet', token='o.abc'), 'info', 'Deploy', 'done', TS)
    assert (ok, err) == (True, '')
    call = post.last
    assert call['url'] == 'https://api.pushbullet.com/v2/pushes'
    assert call['headers'] == {'Access-Token': 'o.abc'}
    assert call['json'] == {'type': 'note', 'title': 'Deploy', 'body': 'done'}
    assert call['timeout'] == 5


def test_telegram_url_body_and_html_mode(post):
    ok, err = np.send(_channel('telegram', token='123:ABC', token2='-100999'), 'error', 'Alert', 'router down', TS)
    assert (ok, err) == (True, '')
    call = post.last
    assert call['url'] == 'https://api.telegram.org/bot123:ABC/sendMessage'
    assert call['json']['chat_id'] == '-100999'
    assert call['json']['parse_mode'] == 'HTML'
    assert 'disable_notification' not in call['json']
    assert call['timeout'] == 5


def test_telegram_escapes_interpolated_values(post):
    np.send(_channel('telegram', token='t', token2='c'), 'error', 'a & b', 'host <foo> & "bar"', TS)
    text = post.last['json']['text']
    assert '<b>a &amp; b</b>' in text
    assert '&lt;foo&gt; &amp; "bar"' in text
    assert '<foo>' not in text


def test_telegram_silent_for_info_and_success(post):
    for type_ in ('info', 'success'):
        np.send(_channel('telegram', token='t', token2='c'), type_, 'T', 'm', TS)
        assert post.last['json']['disable_notification'] is True
    for type_ in ('warning', 'error'):
        np.send(_channel('telegram', token='t', token2='c'), type_, 'T', 'm', TS)
        assert 'disable_notification' not in post.last['json']


def test_telegram_truncates_at_4096(post):
    np.send(_channel('telegram', token='t', token2='c'), 'error', 'T', 'x' * 9000, TS)
    assert len(post.last['json']['text']) == 4096


def test_missing_required_field_is_reported_not_sent(post):
    ok, err = np.send(_channel('gotify', url='https://g.test'), 'info', 'T', 'm', TS)
    assert not ok
    assert 'token' in err
    assert post.calls == []


def test_unknown_kind_never_posts(post):
    ok, err = np.send(_channel('smoke-signal', url='https://x.test'), 'info', 'T', 'm', TS)
    assert not ok
    assert 'smoke-signal' in err
    assert post.calls == []


def test_http_error_is_returned_not_raised(monkeypatch):
    p = _Post(_Resp(status_code=404, text='not found'))
    monkeypatch.setattr(np.requests, 'post', p)
    ok, err = np.send(_channel('discord', url='https://d.test/h'), 'info', 'T', 'm', TS)
    assert not ok
    assert '404' in err and 'not found' in err


def test_transport_exception_is_swallowed(monkeypatch):
    def boom(url, **kwargs):
        raise np.requests.exceptions.ConnectionError('name resolution failed')
    monkeypatch.setattr(np.requests, 'post', boom)
    ok, err = np.send(_channel('ntfy', url='https://n.test/t'), 'info', 'T', 'm', TS)
    assert not ok
    assert 'name resolution failed' in err


def test_timeout_reports_the_timeout(monkeypatch):
    def boom(url, **kwargs):
        raise np.requests.exceptions.Timeout()
    monkeypatch.setattr(np.requests, 'post', boom)
    ok, err = np.send(_channel('telegram', token='t', token2='c'), 'info', 'T', 'm', TS)
    assert not ok
    assert 'timed out' in err


def test_non_dict_channel_is_rejected():
    assert np.send(None, 'info', 'T', 'm', TS) == (False, 'invalid channel')
