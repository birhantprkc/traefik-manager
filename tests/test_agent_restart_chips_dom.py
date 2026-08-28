import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODAL = os.path.join(ROOT, 'templates', 'modals', 'settings_modal.html')
JS = os.path.join(ROOT, 'static', 'js', 'settings-modal.js')

CHIP = re.compile(
    r'<button[^>]*class="agent-chip[^"]*"[^>]*data-method="([^"]*)"[^>]*'
    r"onclick=\"selectRestartMethod\('([^']*)',this\)\"")


def _chips():
    with open(MODAL, encoding='utf-8') as f:
        return CHIP.findall(f.read())


def test_every_restart_chip_carries_a_data_method():
    chips = _chips()
    assert len(chips) == 4, f'expected 4 restart chips with data-method, found {len(chips)}'


def test_data_method_matches_the_value_passed_to_selectrestartmethod():
    for data_method, arg in _chips():
        assert data_method == arg, (
            f'chip data-method="{data_method}" does not match '
            f"selectRestartMethod('{arg}') - the highlight would miss it")


def test_selectrestartmethod_falls_back_to_data_method():
    with open(JS, encoding='utf-8') as f:
        src = f.read()
    body = src.split('function selectRestartMethod', 1)[1].split('\n}', 1)[0]
    assert 'data-method' in body, \
        'selectRestartMethod must resolve the chip from the method when btn is null'
