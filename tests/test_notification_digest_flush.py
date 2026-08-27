import time

import core.notifications as notif
import core.settings as settings_mod


def _channel(**over):
    ch = {'id': 'c1', 'kind': 'ntfy', 'url': 'https://ntfy.example.com/tm',
          'enabled': True, 'digest': 'hourly', 'quiet_hours': '',
          'categories': list(settings_mod.CHANNEL_CATEGORIES),
          'min_severity': 'info'}
    ch.update(over)
    return ch


def _install(monkeypatch, ch, sent):
    monkeypatch.setattr(notif.settings_mod, 'load_settings',
                        lambda: {'notification_channels': [ch]})
    monkeypatch.setattr(notif, '_deliver',
                        lambda c, t, m, ts, cat: sent.append((c['id'], t, m)))


def _queue_one(cid='c1', started=None):
    notif.queue_add(cid, 'info', 'something happened', '2026-08-26 10:00:00', 'traefik')
    if started is not None:
        with notif._notif_lock, notif._file_lock():
            q = notif._queue_read()
            q[cid]['started'] = started
            notif._queue_write(q)


def test_an_hourly_digest_is_not_sent_before_its_window_ends(monkeypatch):
    sent = []
    _install(monkeypatch, _channel(digest='hourly'), sent)
    _queue_one(started=time.time())
    assert notif.flush_queue() == 0
    assert sent == [], 'an hourly digest must hold until the hour is up'


def test_an_hourly_digest_is_sent_once_the_window_has_passed(monkeypatch):
    sent = []
    _install(monkeypatch, _channel(digest='hourly'), sent)
    _queue_one(started=time.time() - 3601)
    assert notif.flush_queue() == 1
    assert len(sent) == 1
    assert 'something happened' in sent[0][2]


def test_a_daily_digest_still_holds_after_an_hour(monkeypatch):
    sent = []
    _install(monkeypatch, _channel(digest='daily'), sent)
    _queue_one(started=time.time() - 3601)
    assert notif.flush_queue() == 0
    assert sent == []


def test_a_quiet_hours_hold_flushes_as_soon_as_the_window_ends(monkeypatch):
    """An immediate channel queued during quiet hours has no digest period."""
    sent = []
    _install(monkeypatch, _channel(digest='immediate'), sent)
    _queue_one(started=time.time())
    assert notif.flush_queue() == 1
    assert len(sent) == 1


def test_the_monitor_hook_drains_the_queue(monkeypatch):
    sent = []
    _install(monkeypatch, _channel(digest='hourly'), sent)
    _queue_one(started=time.time() - 7200)
    assert notif.flush_due() == []
    assert len(sent) == 1, 'flush_due is what the monitor calls, so it must deliver'


def test_queue_add_stamps_the_window_start(monkeypatch):
    _install(monkeypatch, _channel(), [])
    before = time.time()
    _queue_one()
    with notif._notif_lock, notif._file_lock():
        q = notif._queue_read()
    assert isinstance(q['c1'].get('started'), (int, float))
    assert q['c1']['started'] >= before - 1


def test_the_monitor_actually_schedules_the_flush(app_module):
    """The digest shipped with no caller at all, so pin the registration.

    Without a scheduled flush every hourly and daily channel queues forever
    and the user receives nothing.
    """
    from core import monitor as monitor_mod
    names = [name for name, _interval, _fn in monitor_mod._checks]
    assert 'notify-flush' in names, f'no flush check registered, found {names}'
    interval = next(i for n, i, _ in monitor_mod._checks if n == 'notify-flush')
    assert interval <= 300, 'the flush must run often enough to close an hourly window promptly'
