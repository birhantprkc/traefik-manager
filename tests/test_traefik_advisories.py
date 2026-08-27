import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, 'scripts', 'test_traefik_advisories.mjs')


def test_the_advisory_driver_ships_with_the_repo():
    assert os.path.isfile(DRIVER), (
        'scripts/test_traefik_advisories.mjs is the only executable coverage the '
        'security advisory version ranges have; without it a wrong boundary either '
        'hides a real advisory or nags users who are already patched')


def test_advisory_version_ranges_hold():
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed, run scripts/test_traefik_advisories.mjs where it is')
    proc = subprocess.run([node, DRIVER], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, (
        'the advisory driver failed:\n%s\n%s' % (proc.stdout, proc.stderr))
