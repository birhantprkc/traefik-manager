import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, 'scripts', 'test_tooling_card.mjs')


def test_the_driver_ships_with_the_repo():
    assert os.path.isfile(DRIVER)


def test_the_tooling_card_diagnoses_correctly():
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed, run scripts/test_tooling_card.mjs where it is')
    proc = subprocess.run([node, DRIVER], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, (
        'the tooling card driver failed:\n%s\n%s' % (proc.stdout, proc.stderr))
