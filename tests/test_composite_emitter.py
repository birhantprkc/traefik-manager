import pytest

from core import composite_services as cs
from core import service_ownership as own


def _manual(addr, weight=1, percent=0, scheme='http'):
    return {'kind': 'manual', 'address': addr, 'scheme': scheme,
            'weight': weight, 'percent': percent}


def _ref(name, weight=1, percent=0):
    return {'kind': 'service', 'name': name, 'weight': weight, 'percent': percent}


def test_every_manual_row_becomes_its_own_child_with_its_own_weight():
    block, owned, names = cs.build('api', 'weighted',
                                   [_manual('10.0.0.10:80', 9), _manual('10.0.0.11:80', 1)])
    assert names == ['api-backend-1', 'api-backend-2']
    assert block == {'weighted': {'services': [
        {'name': 'api-backend-1', 'weight': 9},
        {'name': 'api-backend-2', 'weight': 1},
    ]}}
    assert owned['api-backend-1'] == {'loadBalancer': {'servers': [{'url': 'http://10.0.0.10:80'}]}}
    assert owned['api-backend-2'] == {'loadBalancer': {'servers': [{'url': 'http://10.0.0.11:80'}]}}


def test_ninety_ten_between_two_raw_addresses_is_expressible():
    block, _owned, _names = cs.build('api', 'weighted',
                                     [_manual('a:80', 9), _manual('b:80', 1)])
    weights = [s['weight'] for s in block['weighted']['services']]
    assert weights == [9, 1], 'this is the case the collapsed design could not express'


def test_a_referenced_service_creates_no_child():
    block, owned, names = cs.build('api', 'weighted', [_manual('a:80'), _ref('canary')])
    assert names == ['api-backend-1', 'canary']
    assert set(owned) == {'api-backend-1'}, 'a referenced service must never be copied'


def test_the_scheme_is_honoured():
    _b, owned, _n = cs.build('api', 'weighted', [_manual('a:443', scheme='https')])
    assert owned['api-backend-1']['loadBalancer']['servers'][0]['url'] == 'https://a:443'


def test_an_address_with_its_own_scheme_is_left_alone():
    _b, owned, _n = cs.build('api', 'weighted', [_manual('https://a:443', scheme='http')])
    assert owned['api-backend-1']['loadBalancer']['servers'][0]['url'] == 'https://a:443'


def test_mirroring_uses_the_first_row_as_the_main_service():
    block, _owned, _names = cs.build('api', 'mirroring',
                                     [_manual('a:80'), _ref('shadow', percent=10)])
    assert block == {'mirroring': {'service': 'api-backend-1',
                                   'mirrors': [{'name': 'shadow', 'percent': 10}]}}


def test_a_mirror_with_no_percent_is_still_written_explicitly():
    block, _owned, _names = cs.build('api', 'mirroring', [_manual('a:80'), _ref('shadow')])
    assert block['mirroring']['mirrors'] == [{'name': 'shadow', 'percent': 0}]


def test_mirroring_with_a_single_row_writes_no_mirrors_key():
    block, _owned, _names = cs.build('api', 'mirroring', [_manual('a:80')])
    assert block == {'mirroring': {'service': 'api-backend-1'}}


def test_failover_maps_the_first_two_rows():
    block, _owned, _names = cs.build('api', 'failover', [_manual('a:80'), _ref('backup')])
    assert block == {'failover': {'service': 'api-backend-1', 'fallback': 'backup'}}


def test_failover_with_one_row_has_no_fallback():
    block, _owned, _names = cs.build('api', 'failover', [_manual('a:80')])
    assert block == {'failover': {'service': 'api-backend-1'}}


@pytest.mark.parametrize('bad', ['highestRandomWeight', '', 'nonsense'])
def test_an_unsupported_type_builds_nothing(bad):
    assert cs.build('api', bad, [_manual('a:80')]) == (None, {}, [])


def test_a_plain_load_balancer_builds_servers_and_owns_nothing():
    block, owned, names = cs.build('api', 'loadBalancer',
                                   [_manual('a:80'), _manual('b:443', scheme='https')])
    assert block == {'loadBalancer': {'servers': [
        {'url': 'http://a:80'}, {'url': 'https://b:443'}]}}
    assert owned == {} and names == []


def test_a_load_balancer_ignores_service_rows():
    block, _owned, _names = cs.build('api', 'loadBalancer', [_ref('other')])
    assert block is None, 'a load balancer holds addresses, not service references'


def test_editing_a_load_balancer_keeps_its_other_settings():
    section = {'svc': {'loadBalancer': {'servers': [{'url': 'http://old:80'}],
                                        'passHostHeader': False},
                       'middlewares': ['secure@file']}}
    block, owned, _n = cs.build('svc', 'loadBalancer', [_manual('new:80')])
    cs.merge_into(section, 'svc', block, owned)
    lb = section['svc']['loadBalancer']
    assert lb['servers'] == [{'url': 'http://new:80'}]
    assert lb['passHostHeader'] is False
    assert section['svc']['middlewares'] == ['secure@file']


def test_no_children_builds_nothing():
    assert cs.build('api', 'weighted', []) == (None, {}, [])


def test_rows_with_no_address_or_name_are_dropped():
    _b, _o, names = cs.build('api', 'weighted',
                             [_manual(''), _ref(''), _manual('a:80')])
    assert names == ['api-backend-1']


def test_a_bad_weight_falls_back_to_one():
    block, _o, _n = cs.build('api', 'weighted', [{'kind': 'manual', 'address': 'a:80',
                                                  'weight': 'lots'}])
    assert block['weighted']['services'][0]['weight'] == 1


def test_merging_replaces_the_previous_composite_type():
    section = {'api-service': {'weighted': {'services': [{'name': 'old'}]},
                               'middlewares': ['secure@file']}}
    block, owned, _n = cs.build('api', 'failover', [_manual('a:80')])
    cs.merge_into(section, 'api-service', block, owned)
    assert 'weighted' not in section['api-service'], 'the stale type must go'
    assert 'failover' in section['api-service']


def test_merging_preserves_siblings_the_emitter_does_not_own():
    section = {'api-service': {'loadBalancer': {'servers': []},
                               'middlewares': ['secure@file']}}
    block, owned, _n = cs.build('api', 'weighted', [_manual('a:80')])
    cs.merge_into(section, 'api-service', block, owned)
    assert section['api-service']['middlewares'] == ['secure@file'], \
        'service.middlewares sits outside the type block and must survive'
    assert 'loadBalancer' not in section['api-service']


def test_merging_updates_an_existing_child_in_place():
    section = {'api-backend-1': {'loadBalancer': {'servers': [{'url': 'http://old:80'}],
                                                  'passHostHeader': False}}}
    block, owned, _n = cs.build('api', 'weighted', [_manual('new:80')])
    cs.merge_into(section, 'api-service', block, owned)
    child = section['api-backend-1']['loadBalancer']
    assert child['servers'] == [{'url': 'http://new:80'}]
    assert child['passHostHeader'] is False, 'child settings must not be rebuilt away'


def test_orphan_children_are_dropped_when_rows_are_removed():
    section = {'api-backend-1': {}, 'api-backend-2': {}, 'api-backend-3': {},
               'other-backend-1': {}}
    dropped = cs.drop_orphan_children(section, 'api', {'api-backend-1'})
    assert sorted(dropped) == ['api-backend-2', 'api-backend-3']
    assert 'other-backend-1' in section, 'another route\'s children must not be touched'


def test_the_ledger_records_the_parent_and_every_owned_child():
    block, owned, _n = cs.build('api', 'weighted', [_manual('a:80'), _ref('canary')])
    entries = cs.ledger_entries('api-service', block, owned)
    assert own.ledger_key('api-service') in entries
    assert own.ledger_key('api-backend-1') in entries
    assert own.ledger_key('canary') not in entries, 'a referenced service is not ours to claim'


def test_the_parent_ledger_entry_round_trips_through_is_owned():
    block, owned, _n = cs.build('api', 'weighted', [_manual('a:80'), _ref('canary')])
    entries = cs.ledger_entries('api-service', block, owned)
    assert own.is_owned('api-service', block, entries)


def test_agent_ledger_entries_are_namespaced():
    block, owned, _n = cs.build('api', 'weighted', [_manual('a:80')])
    entries = cs.ledger_entries('api-service', block, owned, agent_id='a1')
    assert all(k.startswith('agent_a1::') for k in entries)


def test_sticky_on_a_weighted_service_is_not_destroyed():
    section = {'api-service': {'weighted': {
        'services': [{'name': 'old', 'weight': 1}],
        'sticky': {'cookie': {'name': 'lb'}},
        'healthCheck': {},
    }}}
    block, owned, _n = cs.build('api', 'weighted', [_manual('a:80')])
    cs.merge_into(section, 'api-service', block, owned)
    weighted = section['api-service']['weighted']
    assert weighted['sticky'] == {'cookie': {'name': 'lb'}}, \
        'sticky lives inside the weighted block and Traefik Manager does not author it'
    assert 'healthCheck' in weighted
    assert weighted['services'] == [{'name': 'api-backend-1', 'weight': 1}]


def test_mirror_body_settings_are_not_destroyed():
    section = {'api-service': {'mirroring': {
        'service': 'old', 'mirrorBody': False, 'maxBodySize': 1024,
        'mirrors': [{'name': 'gone', 'percent': 5}],
    }}}
    block, owned, _n = cs.build('api', 'mirroring', [_manual('a:80'), _ref('shadow', percent=10)])
    cs.merge_into(section, 'api-service', block, owned)
    mirroring = section['api-service']['mirroring']
    assert mirroring['mirrorBody'] is False
    assert mirroring['maxBodySize'] == 1024
    assert mirroring['service'] == 'api-backend-1'
    assert mirroring['mirrors'] == [{'name': 'shadow', 'percent': 10}]


def test_a_fallback_that_is_removed_is_still_dropped():
    section = {'api-service': {'failover': {'service': 'a', 'fallback': 'b'}}}
    block, owned, _n = cs.build('api', 'failover', [_manual('a:80')])
    cs.merge_into(section, 'api-service', block, owned)
    assert 'fallback' not in section['api-service']['failover'], \
        'keys we do author must still be removable'
