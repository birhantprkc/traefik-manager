import json


def _write_log(tmp_path, n, trailing_newline=True, blank_between=False):
    p = tmp_path / 'access.log'
    rows = [json.dumps({'RequestHost': 'a.example.com', 'DownstreamStatus': 200,
                        'RequestMethod': 'GET', 'RequestPath': '/%d' % i})
            for i in range(n)]
    sep = '\n\n' if blank_between else '\n'
    p.write_text(sep.join(rows) + ('\n' if trailing_newline else ''), encoding='utf-8')
    return str(p)


def _use(monkeypatch, path):
    monkeypatch.setenv('ACCESS_LOG_PATH', path)


def test_requesting_n_lines_returns_n(client, tmp_path, monkeypatch):
    _use(monkeypatch, _write_log(tmp_path, 600))
    for want in (100, 200, 500):
        got = len(client.get('/api/traefik/logs?lines=%d' % want).get_json()['lines'])
        assert got == want, 'asked for %d, got %d' % (want, got)


def test_no_trailing_newline_still_returns_n(client, tmp_path, monkeypatch):
    _use(monkeypatch, _write_log(tmp_path, 300, trailing_newline=False))
    assert len(client.get('/api/traefik/logs?lines=100').get_json()['lines']) == 100


def test_a_short_log_returns_everything_it_has(client, tmp_path, monkeypatch):
    _use(monkeypatch, _write_log(tmp_path, 7))
    assert len(client.get('/api/traefik/logs?lines=100').get_json()['lines']) == 7


def test_blank_lines_do_not_consume_the_budget(client, tmp_path, monkeypatch):
    _use(monkeypatch, _write_log(tmp_path, 50, blank_between=True))
    lines = client.get('/api/traefik/logs?lines=50').get_json()['lines']
    assert len(lines) == 50
    assert all(l.strip() for l in lines)
