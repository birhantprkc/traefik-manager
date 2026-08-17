import os
import stat
import threading
import time

import core.config as config_mod


def _doc(rule):
    return {'http': {'routers': {'r': {'rule': rule, 'service': 's'}},
                     'services': {'s': {'loadBalancer': {'servers': [{'url': 'http://a:1'}]}}}}}


def test_a_reader_never_sees_a_partial_file(tmp_path):
    path = str(tmp_path / 'dynamic.yml')
    short = 'Host(`a.example.com`)'
    long_ = 'Host(`prowlarr.example.com`) && (PathPrefix(`/api`) || PathRegexp(`^/[0-9]+/(api|download)`))'
    config_mod.save_config(_doc(short), path)

    good = set()
    with open(path) as f:
        good.add(f.read())
    config_mod.save_config(_doc(long_), path)
    with open(path) as f:
        good.add(f.read())

    seen = []
    stop = threading.Event()

    def watcher():
        while not stop.is_set():
            try:
                with open(path) as f:
                    seen.append(f.read())
            except OSError:
                seen.append('__MISSING__')
            time.sleep(0.0002)

    t = threading.Thread(target=watcher, daemon=True)
    t.start()
    for i in range(40):
        config_mod.save_config(_doc(long_ if i % 2 else short), path)
        time.sleep(0.002)
    stop.set()
    t.join(timeout=2)

    bad = [x for x in set(seen) if x not in good]
    assert seen, 'the watcher never read the file'
    assert not bad, 'reader saw %d state(s) that were never written, e.g. %r' % (
        len(bad), (bad[0][:120] if bad else ''))


def test_the_destination_keeps_its_permissions(tmp_path):
    path = str(tmp_path / 'dynamic.yml')
    config_mod.save_config(_doc('Host(`a.example.com`)'), path)
    os.chmod(path, 0o640)
    config_mod.save_config(_doc('Host(`b.example.com`)'), path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o640


def test_no_temp_files_are_left_behind(tmp_path):
    path = str(tmp_path / 'dynamic.yml')
    for _ in range(5):
        config_mod.save_config(_doc('Host(`a.example.com`)'), path)
    leftovers = [f for f in os.listdir(str(tmp_path)) if '.tmp.' in f]
    assert not leftovers, leftovers
