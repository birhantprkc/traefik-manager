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
