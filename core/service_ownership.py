from core import env

LEDGER_KIND = 'composite-service'
COMPOSITE_TYPES = ('weighted', 'mirroring', 'failover', 'highestRandomWeight')


def ledger_key(name: str, agent_id: str = '') -> str:
    base = f'svc::{name}'
    return f'agent_{agent_id}::{base}' if agent_id else base


def composite_type(svc_def) -> str:
    if not isinstance(svc_def, dict):
        return ''
    for t in COMPOSITE_TYPES:
        if isinstance(svc_def.get(t), dict):
            return t
    return ''


def child_names(svc_def) -> list:
    t = composite_type(svc_def)
    if not t:
        return []
    block = svc_def.get(t) or {}
    out = []
    if t in ('weighted', 'highestRandomWeight'):
        for child in (block.get('services') or []):
            if isinstance(child, dict) and child.get('name'):
                out.append(str(child['name']))
    elif t == 'mirroring':
        if block.get('service'):
            out.append(str(block['service']))
        for child in (block.get('mirrors') or []):
            if isinstance(child, dict) and child.get('name'):
                out.append(str(child['name']))
    elif t == 'failover':
        for key in ('service', 'fallback'):
            if block.get(key):
                out.append(str(block[key]))
    return out


def ledger_entry(svc_def, config_file: str = '') -> dict:
    return {
        'kind':     LEDGER_KIND,
        'type':     composite_type(svc_def),
        'children': child_names(svc_def),
        'file':     config_file,
    }


def is_owned(name: str, svc_def, ledger, agent_id: str = '') -> bool:
    entry = (ledger or {}).get(ledger_key(name, agent_id))
    if not isinstance(entry, dict) or entry.get('kind') != LEDGER_KIND:
        return False
    current = composite_type(svc_def)
    if not current or current != entry.get('type'):
        return False
    recorded = entry.get('children')
    if not isinstance(recorded, list):
        return False
    return [str(c) for c in recorded] == child_names(svc_def)


def _live_service_names(configs) -> set:
    names = set()
    for cfg in configs:
        for section in ('http', 'tcp', 'udp'):
            for key in ((cfg.get(section) or {}).get('services') or {}):
                if isinstance(key, str):
                    names.add(key)
    return names


def prune(ledger, configs, agent_id: str = '') -> tuple:
    if not isinstance(ledger, dict):
        return {}, False
    live = _live_service_names(configs)
    prefix = f'agent_{agent_id}::svc::' if agent_id else 'svc::'
    kept = {}
    dropped = False
    for key, value in ledger.items():
        if not (isinstance(key, str) and key.startswith(prefix)):
            kept[key] = value
            continue
        if not (isinstance(value, dict) and value.get('kind') == LEDGER_KIND):
            kept[key] = value
            continue
        if key[len(prefix):] in live:
            kept[key] = value
        else:
            dropped = True
            env.logger.info(f"Dropping stale service ledger entry {key!r}")
    return kept, dropped
