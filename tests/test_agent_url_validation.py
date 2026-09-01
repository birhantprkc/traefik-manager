import json

import pytest

import core.agents_store as store


def _put(client, agent_id, payload):
    return client.put('/api/agents/' + agent_id, data=json.dumps(payload),
                      content_type='application/json',
                      headers={'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'})


def _post(client, payload):
    return client.post('/api/agents', data=json.dumps(payload),
                       content_type='application/json',
                       headers={'X-CSRF-Token': 'testtoken', 'X-Requested-With': 'fetch'})


@pytest.fixture
def one_agent():
    store.save_agents_file([{'id': 'a1', 'name': 'alpha',
                             'url': 'http://a1:8090', 'api_key': 'k1'}])
    return 'a1'


@pytest.mark.parametrize('bad', ['a1:8090', 'ftp://a1:8090', 'http://', '   ', 'https://'])
def test_a_url_the_agent_cannot_be_reached_on_is_rejected(client, one_agent, bad):
    r = _put(client, one_agent, {'url': bad})
    assert r.status_code == 400, '%r was accepted' % bad
    assert store.load_agents()[0]['url'] == 'http://a1:8090', 'the stored url must not change'


def test_a_rejected_url_is_never_coerced_to_empty(client, one_agent):
    _put(client, one_agent, {'url': 'a1:8090'})
    assert store.load_agents()[0]['url'], 'blanking the url would leave the agent unrecoverable from the UI'


@pytest.mark.parametrize('good', ['http://a2:8090', 'https://agent.example.com',
                                  'http://10.0.0.5:8090/'])
def test_a_reachable_url_is_accepted(client, one_agent, good):
    r = _put(client, one_agent, {'url': good})
    assert r.status_code < 400, r.get_data(as_text=True)
    assert store.load_agents()[0]['url'] == good.rstrip('/')


def test_create_rejects_a_scheme_less_url(client):
    store.save_agents_file([])
    r = _post(client, {'name': 'beta', 'url': 'beta:8090'})
    assert r.status_code == 400
    assert store.load_agents() == []


def test_an_empty_name_is_rejected_on_update(client, one_agent):
    r = _put(client, one_agent, {'name': '   '})
    assert r.status_code == 400
    assert store.load_agents()[0]['name'] == 'alpha'


def test_a_long_name_is_truncated_on_update_like_create(client, one_agent):
    r = _put(client, one_agent, {'name': 'x' * 200})
    assert r.status_code < 400, r.get_data(as_text=True)
    assert len(store.load_agents()[0]['name']) == 100
