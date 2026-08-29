import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as fh:
        return fh.read()


def _mobile_rows():
    html = _read('templates', 'modals', 'settings_modal.html')
    root = html.split('id="settingsMobileRoot"', 1)[1]
    return re.findall(r'<button class="settings-mobile-row[^"]*"[^>]*onclick="([^"]+)"', root)


def test_every_local_only_row_is_hidden_for_an_agent():
    js = _read('static', 'js', 'settings-modal.js')
    pats = js.split('AGENT_HIDDEN_MOBILE_ROWS = [', 1)[1].split(']', 1)[0]
    covered = re.findall(r'"([^"]+)"', pats)
    rows = _mobile_rows()
    for target in ("switchSettingsPanel('connection')",
                   "switchSettingsPanel('notifications')",
                   "switchSettingsPanel('auth')",
                   "openSettingsChild('system', 'crowdsec')"):
        assert target in rows, 'markup changed: %s' % target
        assert any(c in target for c in covered), \
            '%s stays visible on mobile while an agent is active' % target


def test_the_auth_children_are_hidden_with_their_parent():
    js = _read('static', 'js', 'settings-modal.js')
    pats = js.split('AGENT_HIDDEN_MOBILE_ROWS = [', 1)[1].split(']', 1)[0]
    assert "openSettingsChild('auth'" in pats, (
        'hiding only the parent row leaves Password, API Keys and OIDC reachable, '
        'and those are Host-only')


def test_rows_are_matched_by_target_not_by_id():
    js = _read('static', 'js', 'settings-modal.js')
    body = js.split('function _updateMobileRowsForAgent', 1)[1].split('\n}', 1)[0]
    assert "getAttribute('onclick')" in body, (
        'most mobile rows carry no id, so matching by id silently misses them')


def test_the_filter_runs_for_mobile_as_well_as_desktop():
    js = _read('static', 'js', 'settings-modal.js')
    body = js.split('function _updateSettingsSidebarForAgent', 1)[1].split('\n}', 1)[0]
    assert '_updateMobileRowsForAgent' in body


def test_opening_settings_settles_the_layout_after_a_frame():
    js = _read('static', 'js', 'settings-modal.js')
    assert 'requestAnimationFrame(_settleSettingsLayout)' in js, (
        'measuring in the same frame the modal becomes visible gives pre-layout values, '
        'which is why it only looks right after a scroll')


def test_rotating_re_evaluates_the_mobile_breakpoint():
    js = _read('static', 'js', 'settings-modal.js')
    assert "addEventListener('resize', _applySettingsBreakpoint)" in js
    assert 'orientationchange' in js
    body = js.split('function _applySettingsBreakpoint', 1)[1].split('\n}', 1)[0]
    assert 'window.innerWidth < 640' in body
