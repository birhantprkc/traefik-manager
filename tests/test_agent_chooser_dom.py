import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODAL = os.path.join(ROOT, 'templates', 'modals', 'settings_modal.html')
JS = os.path.join(ROOT, 'static', 'js', 'settings-modal.js')


def _modal():
    with open(MODAL, encoding='utf-8') as fh:
        return fh.read()


def _js():
    with open(JS, encoding='utf-8') as fh:
        return fh.read()


def test_adding_an_agent_offers_two_doors():
    html = _modal()
    assert 'id="agentChooserView"' in html
    assert html.count('class="agent-door"') == 2
    assert "startAgentAdd('cli')" in html
    assert "startAgentAdd('manual')" in html


def test_the_cli_door_is_the_recommended_one():
    html = _modal()
    cli = html.split("startAgentAdd('cli')", 1)[1].split('</button>', 1)[0]
    assert 'Recommended' in cli
    manual = html.split("startAgentAdd('manual')", 1)[1].split('</button>', 1)[0]
    assert 'Recommended' not in manual


def test_add_opens_the_chooser_not_the_wizard():
    body = _js().split('function startAddAgent', 1)[1].split('\n}', 1)[0]
    assert 'agentChooserView' in body
    assert "getElementById('agentWizardView').style.display  = 'none'" in body or \
           "agentWizardView').style.display = 'none'" in body


def test_the_rendered_command_matches_what_the_cli_accepts():
    body = _js().split('function _renderAgentCliStep', 1)[1].split('\n}', 1)[0]
    assert 'get-traefik.xyzlab.dev' in body
    assert '--mode agent' in body, 'the CLI documents agent as the mode that asks which method'
    assert 'export TMA_API_KEY=' in body, \
        'the key must reach the piped shell, and via env so it stays out of ps'
    assert 'sh -c' not in body, 'a wrapped one-liner is easy to mangle when pasted'


def test_the_key_is_not_passed_as_an_argument():
    body = _js().split('function _renderAgentCliStep', 1)[1].split('\n}', 1)[0]
    assert '--api-key' not in body, 'an argument would land in ps output and shell history'


def test_verify_probes_three_states_in_order():
    body = _js().split('async function verifyAgentInstall', 1)[1].split('\n}\n', 1)[0]
    health = body.index('/health')
    keys = body.index('/keys')
    version = body.index('/traefik/version')
    assert health < keys < version, 'unreachable, then wrong key, then not seeing Traefik'
    assert 'keys.status === 401' in body, 'a 401 is what separates a bad key from an unreachable agent'


def test_the_cli_step_is_hidden_unless_selected():
    html = _modal()
    step = html.split('id="agentWizStepCli"', 1)[1][:80]
    assert 'display:none' in step
    show = _js().split('function showAgentWizStep', 1)[1].split('\n}', 1)[0]
    assert "n === 'cli'" in show

def test_creating_an_agent_does_not_close_the_wizard():
    js = _js()
    body = js.split('async function agentWizStep1Next', 1)[1].split('\n}\n', 1)[0]
    assert 'loadAgentsList()' not in body, (
        'loadAgentsList hides agentWizardView and shows agentListView, so calling it here '
        'closes the CLI step the moment it is rendered')
    assert 'refreshAgentRegistry()' in body


def test_saving_agent_config_does_not_close_the_wizard():
    js = _js()
    body = js.split('async function agentWizStep3Save', 1)[1].split('\n}\n', 1)[0]
    assert 'loadAgentsList()' not in body
    assert 'refreshAgentRegistry()' in body


def test_the_registry_refresh_never_switches_views():
    js = _js()
    body = js.split('async function refreshAgentRegistry', 1)[1].split('\n}\n', 1)[0]
    for banned in ('agentListView', 'agentWizardView', 'agentKeysView', 'style.display'):
        assert banned not in body, (
            'a data refresh must not move the user: found %s' % banned)
    assert 'updateServerSwitcher' in body


def test_the_cli_step_survives_to_show_the_key_and_command():
    js = _js()
    body = js.split('async function agentWizStep1Next', 1)[1].split('\n}\n', 1)[0]
    assert "_renderAgentCliStep()" in body
    assert "showAgentWizStep('cli')" in body
    order = body.index("showAgentWizStep('cli')")
    refresh = body.index('refreshAgentRegistry()')
    assert order < refresh, 'the step must render before anything else runs'


def test_both_agent_surfaces_point_at_the_cli_for_management():
    html = _modal()
    assert html.count('tm reconfigure') == 2, \
        'the CLI step and the agent settings screen should both name the management commands'
    for cmd in ('tm status', 'tm logs', 'tm update', 'tm doctor'):
        assert html.count(cmd) >= 2, cmd


def test_the_management_block_sits_in_the_summary_not_behind_compose():
    import re
    html = _modal()
    lines = html.split('\n')
    start = next(n for n, l in enumerate(lines) if 'id="agentSummaryView"' in l)
    depth = 0
    for n in range(start, len(lines)):
        depth += len(re.findall(r'<div\b', lines[n])) - len(re.findall(r'</div>', lines[n]))
        if depth == 0:
            block = '\n'.join(lines[start:n + 1])
            assert 'Manage on the agent' in block, \
                'the tm commands are the point of the summary screen'
            assert 'agentRunOutput' not in block, \
                'compose output belongs behind the Compose settings door'
            return
    raise AssertionError('agentSummaryView never closes')


def test_the_docs_carry_the_same_commands():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, 'docs', 'agent.md'), encoding='utf-8') as fh:
        doc = fh.read()
    assert '## Managing an agent' in doc
    for cmd in ('tm status', 'tm logs', 'tm update', 'tm reconfigure', 'tm doctor'):
        assert cmd in doc, cmd


def test_every_path_back_to_the_list_reloads_it():
    js = _js()
    for fn in ('cancelAddAgent', 'agentWizDone', 'closeAgentKeys'):
        body = js.split('function ' + fn, 1)[1].split('\n}', 1)[0]
        assert 'loadAgentsList()' in body, (
            '%s returns the user to the agent list; without a reload it shows stale data '
            'and a newly added agent is missing until a refresh' % fn)


def test_no_path_shows_the_list_without_loading_it():
    js = _js()
    for fn in ('cancelAddAgent', 'closeAgentKeys'):
        body = js.split('function ' + fn, 1)[1].split('\n}', 1)[0]
        assert "agentListView').style.display  = 'flex'" not in body.replace('  ', ' '), \
            '%s should let loadAgentsList own the view switch' % fn


def test_the_cli_door_records_how_the_agent_was_installed():
    js = _js()
    body = js.split('async function agentWizStep1Next', 1)[1].split('\n}\n', 1)[0]
    assert "install_method" in body and "_agentAddMode === 'cli'" in body


def test_a_cli_installed_agent_hides_the_compose_output():
    js = _js()
    body = js.split('function _applyAgentInstallMethod', 1)[1].split('\n}', 1)[0]
    assert 'agentDockerOutputsWrap' in body
    assert "method === 'cli'" in body


def test_the_manual_path_still_shows_it():
    js = _js()
    body = js.split('function resetAgentWizardCfgFields', 1)[1].split('\n}', 1)[0]
    assert "_applyAgentInstallMethod('manual')" in body, \
        'without this a manual agent inherits the previous agent hidden state'


def test_the_docker_outputs_are_wrapped_together():
    import re
    html = _modal()
    lines = html.split('\n')
    start = next(n for n, l in enumerate(lines) if 'agentDockerOutputsWrap' in l)
    depth = 0
    for n in range(start, len(lines)):
        depth += len(re.findall(r'<div\b', lines[n])) - len(re.findall(r'</div>', lines[n]))
        if depth == 0:
            block = '\n'.join(lines[start:n + 1])
            assert 'agentComposeOutput' in block and 'agentRunOutput' in block
            assert 'Manage on the agent' not in block, \
                'the tm management block must stay visible for cli agents'
            return
    raise AssertionError('wrapper never closes')


def test_the_compose_output_is_folded_away_by_default():
    html = _modal()
    assert 'toggleAgentDockerOutputs()' in html
    assert 'sc-notice-body' in html.split('agentDockerOutputsWrap', 1)[1][:1200], \
        'the outputs should sit inside the collapsible body'
    head = html.split('agentDockerOutputsWrap', 1)[1][:400]
    assert 'sc-notice rounded-lg"' in html.split('agentDockerOutputsWrap', 1)[0][-120:] + head, \
        'no open class in the markup means it starts collapsed'


def test_the_fold_reuses_the_existing_notice_styling():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    css = open(os.path.join(root, 'static', 'css', 'app.css'), encoding='utf-8').read()
    assert '.sc-notice.open .sc-notice-body' in css, \
        'the fold relies on the shared notice CSS rather than a new style'


def test_agent_docs_and_ui_do_not_say_host_for_the_agent_machine():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    html = _modal()
    for phrase in ('on its own host', 'Manage from the host', 'the agent host.'):
        assert phrase not in html, (
            '"host" means the Traefik Manager server in this app, so it reads as the wrong '
            'machine: %s' % phrase)
    doc = open(os.path.join(root, 'docs', 'agent.md'), encoding='utf-8').read()
    assert 'is managed on its own host' not in doc


def test_opening_an_agent_lands_on_the_summary():
    js = _js()
    body = js.split('async function openAgentSetup', 1)[1].split('\n}\n', 1)[0]
    assert 'hideAgentComposeConfig()' in body


def test_identity_is_editable_on_the_edit_screen():
    html = _modal()
    for i in ('agEditName', 'agEditUrl', 'agEditSaveBtn'):
        assert 'id="%s"' % i in html, i
    js = _js()
    assert 'async function saveAgentIdentity' in js
    body = js.split('async function saveAgentIdentity', 1)[1].split('\n}\n', 1)[0]
    assert "JSON.stringify({ name, url })" in body


def test_the_agent_list_no_longer_edits_identity_inline():
    js = _js()
    assert 'inlineEditAgent' not in js, \
        'identity editing lives on the edit screen now, not as pencils in the list'


def test_no_duplicated_element_ids_after_the_split():
    import re
    html = _modal()
    ids = re.findall(r'id="([A-Za-z][\w-]*)"', html)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, 'getElementById returns the first match, so duplicates silently misfire: %s' % dupes
