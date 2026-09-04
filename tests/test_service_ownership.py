from core import service_ownership as own


def _weighted(*children):
    return {'weighted': {'services': [{'name': c} for c in children]}}


def _ledger(name, svc_def, agent_id=''):
    return {own.ledger_key(name, agent_id): own.ledger_entry(svc_def)}


def test_a_composite_type_is_recognised():
    assert own.composite_type(_weighted('a')) == 'weighted'
    assert own.composite_type({'mirroring': {'service': 'm'}}) == 'mirroring'
    assert own.composite_type({'failover': {'service': 'p'}}) == 'failover'
    assert own.composite_type({'highestRandomWeight': {'services': []}}) == 'highestRandomWeight'


def test_a_load_balancer_is_not_a_composite():
    assert own.composite_type({'loadBalancer': {'servers': []}}) == ''
    assert own.composite_type(None) == ''
    assert own.composite_type('nonsense') == ''


def test_children_are_read_for_every_type():
    assert own.child_names(_weighted('a', 'b')) == ['a', 'b']
    assert own.child_names({'mirroring': {'service': 'main', 'mirrors': [{'name': 'shadow'}]}}) \
        == ['main', 'shadow']
    assert own.child_names({'failover': {'service': 'p', 'fallback': 'f'}}) == ['p', 'f']
    assert own.child_names({'loadBalancer': {}}) == []


def test_a_service_traefik_manager_wrote_is_owned():
    svc = _weighted('a', 'b')
    assert own.is_owned('pool', svc, _ledger('pool', svc))


def test_a_hand_written_service_with_no_ledger_key_is_never_owned():
    assert not own.is_owned('pool', _weighted('a', 'b'), {})


def test_a_ledger_key_alone_does_not_claim_a_block():
    ledger = _ledger('pool', _weighted('a', 'b'))
    restored = _weighted('completely', 'different')
    assert not own.is_owned('pool', restored, ledger), \
        'a git restore leaves the ledger behind; it must not claim whatever now sits at that name'


def test_a_changed_type_is_not_owned():
    ledger = _ledger('pool', _weighted('a'))
    assert not own.is_owned('pool', {'failover': {'service': 'a'}}, ledger)


def test_a_hand_edited_child_list_gives_up_ownership():
    svc = _weighted('a', 'b')
    ledger = _ledger('pool', svc)
    edited = _weighted('a', 'b', 'c')
    assert not own.is_owned('pool', edited, ledger), \
        'an external edit must fall back to read-only rather than be overwritten'


def test_child_order_is_part_of_the_identity():
    ledger = _ledger('pool', _weighted('a', 'b'))
    assert not own.is_owned('pool', _weighted('b', 'a'), ledger)


def test_a_service_that_is_gone_is_not_owned():
    ledger = _ledger('pool', _weighted('a'))
    assert not own.is_owned('pool', None, ledger)
    assert not own.is_owned('pool', {'loadBalancer': {'servers': []}}, ledger)


def test_an_entry_of_the_wrong_kind_is_ignored():
    svc = _weighted('a')
    ledger = {own.ledger_key('pool'): {'kind': 'route-headers', 'route': 'x'}}
    assert not own.is_owned('pool', svc, ledger)


def test_agent_keys_are_namespaced():
    assert own.ledger_key('pool') == 'svc::pool'
    assert own.ledger_key('pool', 'a1') == 'agent_a1::svc::pool'
    svc = _weighted('a')
    host_ledger = _ledger('pool', svc)
    assert not own.is_owned('pool', svc, host_ledger, agent_id='a1'), \
        'a host ledger entry must not claim an agent service of the same name'


def _config(*names):
    return {'http': {'services': {n: _weighted('x') for n in names}}}


def test_pruning_drops_entries_whose_service_is_gone():
    svc = _weighted('x')
    ledger = {**_ledger('kept', svc), **_ledger('gone', svc)}
    kept, dropped = own.prune(ledger, [_config('kept')])
    assert dropped
    assert set(kept) == {own.ledger_key('kept')}


def test_pruning_keeps_entries_that_are_still_there():
    ledger = _ledger('kept', _weighted('x'))
    kept, dropped = own.prune(ledger, [_config('kept')])
    assert not dropped
    assert kept == ledger


def test_pruning_never_touches_other_ledger_entries():
    ledger = {
        'tp::api-transport': {'kind': 'route-transport', 'route': 'api'},
        'api-headers': {'kind': 'route-headers', 'route': 'api'},
        **_ledger('gone', _weighted('x')),
    }
    kept, dropped = own.prune(ledger, [_config('other')])
    assert dropped
    assert 'tp::api-transport' in kept and 'api-headers' in kept
    assert own.ledger_key('gone') not in kept


def test_pruning_an_agent_ledger_leaves_the_host_alone():
    svc = _weighted('x')
    ledger = {**_ledger('gone', svc), **_ledger('gone', svc, 'a1')}
    kept, dropped = own.prune(ledger, [_config('other')], agent_id='a1')
    assert dropped
    assert own.ledger_key('gone') in kept, 'pruning one agent must not touch host entries'
    assert own.ledger_key('gone', 'a1') not in kept


def test_pruning_looks_across_every_config_file_and_protocol():
    svc = _weighted('x')
    ledger = {**_ledger('in-http', svc), **_ledger('in-tcp', svc)}
    configs = [{'http': {'services': {'in-http': {}}}}, {'tcp': {'services': {'in-tcp': {}}}}]
    kept, dropped = own.prune(ledger, configs)
    assert not dropped
    assert len(kept) == 2


def test_pruning_survives_a_broken_ledger():
    assert own.prune(None, [_config('a')]) == ({}, False)
    kept, dropped = own.prune({'svc::x': 'not a dict'}, [_config('a')])
    assert kept == {'svc::x': 'not a dict'} and not dropped
