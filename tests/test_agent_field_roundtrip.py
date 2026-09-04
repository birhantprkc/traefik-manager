import core.agents_store as store


def _roundtrip(**extra):
    agent = {'id': 'a1', 'name': 'n', 'url': 'http://a1:8090', 'api_key': 'k'}
    agent.update(extra)
    store.save_agents_file([agent])
    return store.load_agents()[0]


def test_every_field_the_form_saves_survives_a_load():
    a = _roundtrip(traefik_api_user='admin', traefik_api_password='secret',
                   install_method='cli', git_backup_commit_message='chore: backup')
    for field, want in (('traefik_api_user', 'admin'),
                        ('traefik_api_password', 'secret'),
                        ('install_method', 'cli'),
                        ('git_backup_commit_message', 'chore: backup')):
        assert a.get(field) == want, (
            '%s is written by the form but dropped by parse_agent_dict, so the setting '
            'silently does nothing' % field)


def test_install_method_defaults_to_manual():
    assert _roundtrip().get('install_method') == 'manual'
    assert _roundtrip(install_method='nonsense').get('install_method') == 'manual'


def test_the_parser_covers_every_field_the_update_endpoint_accepts():
    import os
    import re
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = open(os.path.join(root, 'app.py'), encoding='utf-8').read()
    updatable = set(re.findall(r"'([a-z_0-9]+)'",
                               app.split('updatable = [', 1)[1].split(']', 1)[0]))
    parser = open(os.path.join(root, 'core', 'agents_store.py'), encoding='utf-8').read()
    parsed = set(re.findall(r"^\s+'([a-z_0-9]+)':", parser, re.M))
    missing = sorted(updatable - parsed)
    assert not missing, (
        'these can be saved but are thrown away on the next load: %s' % missing)
