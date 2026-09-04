import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODAL = os.path.join(ROOT, 'templates', 'modals', 'mw_modal.html')
JS = os.path.join(ROOT, 'static', 'js', 'middlewares.js')


def _modal():
    with open(MODAL, encoding='utf-8') as fh:
        return fh.read()


def _js():
    with open(JS, encoding='utf-8') as fh:
        return fh.read()


def _wizard_templates():
    m = re.search(r'_wizardTemplates = new Set\(\[(.*?)\]\)', _js(), re.S)
    assert m, 'the wizard template set moved or was renamed'
    return set(re.findall(r"'([^']+)'", m.group(1)))


def _key_map():
    m = re.search(r'_wizKeyMap = \{(.*?)\};', _js(), re.S)
    assert m, 'the wizard key map moved or was renamed'
    return dict(re.findall(r"(\w+):\s*'([^']+)'", m.group(1)))


def _form_ids():
    return set(re.findall(r'id="mwWiz-([A-Za-z]+)"', _modal())) - {'none'}


def _option_values():
    return set(re.findall(r'<option value="([A-Za-z]+)"', _modal()))


def _builder_body():
    js = _js()
    start = js.index('function buildYamlFromWizard()')
    end = js.index('\nfunction ', start + 1)
    return js[start:end]


def _builder_keys():
    body = _builder_body()
    assert "_q(" in body, 'the YAML builder moved, so this test scans the wrong code'
    return set(re.findall(r"key === '([A-Za-z]+)'", body))


def test_every_wizard_template_is_selectable():
    missing = _wizard_templates() - _option_values()
    assert not missing, f'no <option> for {sorted(missing)}, so the wizard can never open'


def test_every_wizard_template_has_a_form():
    keymap = _key_map()
    missing = {keymap.get(t, t) for t in _wizard_templates()} - _form_ids()
    assert not missing, f'no mwWiz- block for {sorted(missing)}, so the wizard opens empty'


def test_every_wizard_template_builds_yaml():
    keymap = _key_map()
    missing = {keymap.get(t, t) for t in _wizard_templates()} - _builder_keys()
    assert not missing, f'no YAML branch for {sorted(missing)}, so saving writes nothing'


def test_no_orphan_wizard_forms():
    keymap = _key_map()
    reachable = {keymap.get(t, t) for t in _wizard_templates()}
    orphans = _form_ids() - reachable
    assert not orphans, f'{sorted(orphans)} can never be shown'


def test_wizard_form_ids_are_unique():
    ids = re.findall(r'id="(mwWiz-[A-Za-z]+)"', _modal())
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f'duplicate wizard blocks: {sorted(dupes)}'


def test_wizard_field_ids_are_unique():
    ids = re.findall(r'id="(wiz[A-Za-z]+)"', _modal())
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f'duplicate field ids, so only the first is ever read: {sorted(dupes)}'


def test_every_field_the_builder_reads_exists():
    html = _modal()
    read = set(re.findall(r"_(?:val|lines|chk)\('(wiz[A-Za-z]+)'\s*[,)]", _js()))
    read |= set(re.findall(r"getElementById\('(wiz[A-Za-z]+)'\)", _js()))
    assert len(read) > 30, 'the id scan stopped matching, so this test proves nothing'
    missing = {i for i in read if f'id="{i}"' not in html}
    assert not missing, f'the builder reads fields that do not exist: {sorted(missing)}'


def test_the_six_new_wizards_are_wired():
    for key in ('stripPrefixRegex', 'replacePathRegex', 'errors',
                'contentType', 'grpcWeb', 'passTLSClientCert'):
        assert key in _wizard_templates()
        assert key in _form_ids()
        assert key in _option_values()
        assert key in _builder_keys()


def test_the_error_page_service_picker_is_populated():
    js = _js()
    assert "_populateMwErrorService" in js
    assert "_ensureServicesList" in js, \
        'the picker must read the same service list the route form uses'
