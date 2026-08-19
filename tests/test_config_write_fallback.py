import errno
import os

import core.config as config_mod
from tests.conftest import DYNAMIC_PATH


def test_save_falls_back_to_copy_when_rename_is_blocked(monkeypatch):
    real_replace = os.replace
    attempts = []

    def busy(src, dst):
        if str(dst) == str(DYNAMIC_PATH):
            attempts.append(src)
            raise OSError(errno.EBUSY, 'Resource busy')
        return real_replace(src, dst)

    monkeypatch.setattr(config_mod.os, 'replace', busy)
    config_mod.save_config({'http': {'routers': {'r1': {'rule': 'Host(`a.example.com`)',
                                                        'service': 'svc1'}}}},
                           str(DYNAMIC_PATH))
    assert attempts, 'os.replace was never attempted'
    saved = config_mod.load_config(str(DYNAMIC_PATH))
    assert saved['http']['routers']['r1']['rule'] == 'Host(`a.example.com`)'
    leftovers = [f for f in os.listdir(os.path.dirname(str(DYNAMIC_PATH)))
                 if '.tmp.' in f]
    assert not leftovers, f'tmp files left behind: {leftovers}'


def test_unexpected_rename_errors_still_raise(monkeypatch):
    def denied(src, dst):
        raise OSError(errno.EACCES, 'Permission denied')

    monkeypatch.setattr(config_mod.os, 'replace', denied)
    try:
        config_mod.save_config({'http': {}}, str(DYNAMIC_PATH))
        raised = False
    except OSError as e:
        raised = e.errno == errno.EACCES
    assert raised, 'a real permission error must not be swallowed'
