"""Scheduled background checks that raise notifications.

One process per host runs the loop. The runner is picked with a non-blocking
flock on the config directory, so the extra gunicorn workers stay idle instead
of firing every alert twice.
"""
import calendar
import inspect
import json
import os
import threading
import time

import requests

from core import agents_http as agents_http_mod
from core import certs as certs_mod
from core import config as cfg_mod
from core import crowdsec as crowdsec_mod
from core import env
from core import geoip as geoip_mod
from core import notifications
from core import settings as settings_mod
from core import traefik as traefik_mod
from core.env import logger

try:
    import fcntl
except ImportError:
    fcntl = None

CERT_INTERVAL     = 86400
TRAEFIK_INTERVAL  = 60
AGENT_INTERVAL    = 120
GEOIP_INTERVAL    = 86400
CROWDSEC_INTERVAL = 300

CERT_ALERT_DAYS   = (14, 3, 0)
GEOIP_STALE_DAYS  = 35
AGENT_TIMEOUT     = 5
LOOP_TICK         = 15
HOST_SERVER       = 'host'
KEY_SEP           = '|'

_state     = {}
_cycle_up  = {}
_run_lock  = threading.Lock()
_stop_event = threading.Event()
_thread    = None
_lock_fh   = None


def _now() -> float:
    return time.time()


def _lock_path():
    return os.path.join(env.CONFIG_DIR, '.monitor.lock')


def _state_path():
    return os.path.join(env.CONFIG_DIR, 'monitor.json')


def _read_state():
    try:
        with open(_state_path(), 'r') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_state():
    path = _state_path()
    tmp  = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp, 'w') as f:
            json.dump(_state, f)
        cfg_mod._replace_or_copy(tmp, path)
    except Exception:
        logger.exception("Failed to save monitor state")
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def _section(name):
    section = _state.get(name)
    if not isinstance(section, dict):
        section = {}
        _state[name] = section
    return section


def _server_key(server, subject):
    return f"{server}{KEY_SEP}{subject}"


def _key_server(key):
    return key.split(KEY_SEP, 1)[0] if KEY_SEP in key else HOST_SERVER


def _migrate_host_keys(state):
    for key in [k for k in state if KEY_SEP not in k]:
        state.setdefault(_server_key(HOST_SERVER, key), state.pop(key))
    return state


def _prune(state, known):
    for key in [k for k in state if _key_server(k) not in known]:
        state.pop(key, None)


def _server_msg(name, msg):
    return f"{name}: {msg}" if name else msg


def _notify(type_, msg, category):
    try:
        params = inspect.signature(notifications.add_notification).parameters
    except (TypeError, ValueError):
        params = {}
    takes_category = 'category' in params or any(p.kind == p.VAR_KEYWORD for p in params.values())
    if takes_category:
        notifications.add_notification(type_, msg, category=category)
    else:
        notifications.add_notification(type_, msg)


def _parse_not_after(value):
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S'):
        try:
            return calendar.timegm(time.strptime(value, fmt))
        except ValueError:
            continue
    return None


def _acme_certs():
    out = []
    for configured in settings_mod.get_acme_json_paths():
        path = cfg_mod.readable_config_path(configured)
        if not (path and os.path.exists(path)):
            continue
        try:
            with open(path, 'r') as f:
                raw = f.read().strip()
            data = json.loads(raw) if raw else {}
        except Exception as e:
            logger.debug(f"Monitor could not read {path}: {e}")
            continue
        for resolver_name, resolver_data in (data or {}).items():
            if not isinstance(resolver_data, dict):
                continue
            for c in (resolver_data.get('Certificates') or resolver_data.get('certificates') or []):
                domain = c.get('domain') or {}
                out.append({'resolver': resolver_name,
                            'main': domain.get('main', ''),
                            'not_after': certs_mod._parse_cert_expiry(c.get('certificate', ''))})
    return out


def _all_certs():
    certs = _acme_certs()
    try:
        certs.extend(certs_mod._certs_from_tls_configs())
    except Exception as e:
        logger.debug(f"Monitor could not read file-provider certs: {e}")
    return certs


def _agents():
    return settings_mod.load_settings().get('agents') or []


def _agent_up(agent) -> bool:
    try:
        resp = requests.get(str(agent.get('url') or '').rstrip('/') + '/health', timeout=AGENT_TIMEOUT)
        return resp.status_code == 200
    except Exception as e:
        logger.debug(f"Agent health check failed for {agent.get('name', '')}: {e}")
        return False


def _agent_reachable(agent) -> bool:
    agent_id = str(agent.get('id') or '')
    if agent_id not in _cycle_up:
        _cycle_up[agent_id] = _agent_up(agent)
    return _cycle_up[agent_id]


def _agent_servers():
    servers = []
    for agent in _agents():
        agent_id = str(agent.get('id') or '')
        if agent_id:
            servers.append((agent_id, str(agent.get('name') or agent_id), agent))
    return servers


def _known_servers(servers):
    return {HOST_SERVER} | {server for server, _name, _agent in servers}


def _agent_json(agent, path):
    resp = agents_http_mod._agent_request(agent, 'GET', path)
    if resp.status_code != 200:
        raise RuntimeError(f"{path} returned HTTP {resp.status_code}")
    return resp.json()


def _agent_certs(agent):
    data = _agent_json(agent, '/api/traefik/certs')
    return [c for c in ((data or {}).get('certs') or []) if isinstance(c, dict)]


def _agent_traefik_up(agent) -> bool:
    try:
        return _agent_json(agent, '/api/traefik/overview') is not None
    except Exception as e:
        logger.debug(f"Traefik check failed for agent {agent.get('name', '')}: {e}")
        return False


def _cert_alert(name, main, resolver, days):
    where = f"{main} ({resolver})" if resolver else main
    if days < 0:
        return ('error', _server_msg(name, f"Certificate for {where} expired {abs(days)} day(s) ago"), 'certs')
    if days == 0:
        return ('error', _server_msg(name, f"Certificate for {where} expires today"), 'certs')
    return ('warning', _server_msg(name, f"Certificate for {where} expires in {days} day(s)"), 'certs')


def _cert_sources(servers):
    sources = []
    try:
        sources.append((HOST_SERVER, '', _all_certs()))
    except Exception:
        logger.exception("Certificate check failed for the host")
    for server, name, agent in servers:
        try:
            if _agent_reachable(agent):
                sources.append((server, name, _agent_certs(agent)))
        except Exception:
            logger.exception(f"Certificate check failed for agent {name}")
    return sources


def _check_certs():
    state   = _migrate_host_keys(_section('certs'))
    servers = _agent_servers()
    raised  = []
    seen    = {}
    checked = set()
    now     = _now()
    for server, name, certs in _cert_sources(servers):
        checked.add(server)
        for cert in certs:
            main      = str(cert.get('main') or '').strip()
            not_after = str(cert.get('not_after') or '').strip()
            expiry    = _parse_not_after(not_after) if not_after else None
            if not main or expiry is None:
                continue
            resolver = str(cert.get('resolver') or '')
            key      = _server_key(server, f"{resolver}:{main}")
            entry    = state.get(key)
            if not isinstance(entry, dict) or entry.get('not_after') != not_after:
                entry = {'not_after': not_after, 'fired': []}
            fired   = [d for d in entry.get('fired', []) if isinstance(d, int)]
            days    = int((expiry - now) // 86400)
            crossed = [d for d in CERT_ALERT_DAYS if days <= d]
            if [d for d in crossed if d not in fired]:
                entry['fired'] = sorted(set(fired + crossed), reverse=True)
                raised.append(_cert_alert(name, main, resolver, days))
            seen[key] = entry
    for key, entry in state.items():
        if _key_server(key) not in checked:
            seen.setdefault(key, entry)
    state.clear()
    state.update(seen)
    _prune(state, _known_servers(servers))
    return raised


def _traefik_sources(servers):
    sources = []
    try:
        sources.append((HOST_SERVER, '', traefik_mod.traefik_api_get('/api/overview') is not None))
    except Exception:
        logger.exception("Traefik check failed for the host")
    for server, name, agent in servers:
        try:
            if _agent_reachable(agent):
                sources.append((server, name, _agent_traefik_up(agent)))
        except Exception:
            logger.exception(f"Traefik check failed for agent {name}")
    return sources


def _check_traefik():
    state   = _migrate_host_keys(_section('traefik'))
    servers = _agent_servers()
    raised  = []
    for server, name, up in _traefik_sources(servers):
        key  = _server_key(server, 'up')
        prev = state.get(key)
        state[key] = up
        if up == prev:
            continue
        if up:
            if prev is not None:
                raised.append(('success', _server_msg(name, 'Traefik API is reachable again'), 'traefik'))
        else:
            raised.append(('error', _server_msg(name, 'Traefik API is unreachable'), 'traefik'))
    _prune(state, _known_servers(servers))
    return raised


def _check_agents():
    state   = _section('agents')
    servers = _agent_servers()
    raised  = []
    seen    = {}
    for agent_id, name, agent in servers:
        try:
            up = _agent_reachable(agent)
        except Exception:
            logger.exception(f"Health check failed for agent {name}")
            continue
        prev = state.get(agent_id)
        seen[agent_id] = up
        if up == prev:
            continue
        if up:
            if prev is not None:
                raised.append(('success', f"Agent {name} is back online", 'agent'))
        else:
            raised.append(('error', f"Agent {name} is unreachable", 'agent'))
    known = {agent_id for agent_id, _name, _agent in servers}
    for agent_id, up in state.items():
        if agent_id in known:
            seen.setdefault(agent_id, up)
    state.clear()
    state.update(seen)
    return raised


def _agent_crowdsec(agent):
    try:
        resp = agents_http_mod._agent_request(agent, 'GET', '/api/crowdsec/alerts')
    except Exception as e:
        logger.debug(f"CrowdSec check failed for agent {agent.get('name', '')}: {e}")
        return True, False, []
    if resp.status_code == 404:
        return False, False, []
    if resp.status_code != 200:
        return True, False, []
    try:
        alerts = resp.json()
    except Exception as e:
        logger.debug(f"CrowdSec alerts from agent {agent.get('name', '')} were unreadable: {e}")
        return True, False, []
    return True, True, [a for a in (alerts or []) if isinstance(a, dict)]


def _crowdsec_summary(alerts, last_id):
    seen    = last_id if isinstance(last_id, int) else None
    highest = seen or 0
    fresh   = []
    for alert in alerts:
        try:
            alert_id = int(alert.get('id') or 0)
        except (TypeError, ValueError):
            alert_id = 0
        highest = max(highest, alert_id)
        if seen is not None and alert_id > seen:
            fresh.append(alert)
    if seen is None or not fresh:
        return '', highest
    return crowdsec_mod.summarise_alerts(fresh), highest


def _check_crowdsec_agents():
    state   = _section('crowdsec')
    servers = _agent_servers()
    raised  = []
    for server, name, agent in servers:
        key = _server_key(server, 'lapi')
        try:
            if not _agent_reachable(agent):
                continue
            configured, up, alerts = _agent_crowdsec(agent)
            if not configured:
                state.pop(key, None)
                continue
            entry = state.get(key)
            entry = dict(entry) if isinstance(entry, dict) else {}
            prev  = entry.get('up')
            entry['up'] = up
            if up != prev:
                if up:
                    if prev is not None:
                        raised.append(('success', _server_msg(name, 'CrowdSec LAPI is reachable again'), 'crowdsec'))
                else:
                    raised.append(('error', _server_msg(name, 'CrowdSec LAPI is unreachable'), 'crowdsec'))
            if up:
                msg, entry['last_id'] = _crowdsec_summary(alerts, entry.get('last_id'))
                if msg:
                    raised.append(('warning', _server_msg(name, msg), 'crowdsec'))
            state[key] = entry
        except Exception:
            logger.exception(f"CrowdSec check failed for agent {name}")
    _prune(state, _known_servers(servers))
    return raised


def _check_geoip():
    state = _section('geoip')
    if not geoip_mod._geoip_enabled():
        state['stale'] = False
        return []
    path  = geoip_mod._geoip_db_path()
    stale = True
    if os.path.exists(path):
        try:
            stale = (_now() - os.path.getmtime(path)) > GEOIP_STALE_DAYS * 86400
        except OSError:
            stale = True
    if not stale:
        state['stale'] = False
        return []
    was_stale = bool(state.get('stale'))
    ok, info  = geoip_mod._geoip_download()
    state['stale'] = not ok
    if ok:
        return [('success', f"GeoIP database updated to DB-IP {info}", 'update')]
    if was_stale:
        return []
    return [('warning', f"GeoIP database is out of date and could not be updated: {info}", 'update')]


def register(name: str, interval_seconds: int, fn):
    """Add a check to the schedule.

    fn takes no arguments and may return an iterable of (type, message, category)
    tuples for the monitor to raise, or None if it raises its own notifications.
    Registering a name twice replaces the earlier check.
    """
    entry = (str(name), max(1, int(interval_seconds)), fn)
    for i, check in enumerate(_checks):
        if check[0] == entry[0]:
            _checks[i] = entry
            return
    _checks.append(entry)


def run_checks_once(force: bool = False) -> list:
    """Run every check whose interval has elapsed and return the notifications raised.

    Each item is a (type, message, category) tuple. force runs every check
    regardless of when it last ran.
    """
    raised = []
    with _run_lock:
        _state.clear()
        _state.update(_read_state())
        _cycle_up.clear()
        due = _section('due')
        ran = False
        for name, interval, fn in list(_checks):
            last = due.get(name)
            if not force and isinstance(last, (int, float)) and (_now() - last) < interval:
                continue
            due[name] = _now()
            ran = True
            try:
                result = fn() or []
            except Exception:
                logger.exception(f"Monitor check {name!r} failed")
                continue
            for item in result:
                try:
                    type_, msg, category = item
                except (TypeError, ValueError):
                    logger.warning(f"Monitor check {name!r} returned an unusable result: {item!r}")
                    continue
                raised.append((str(type_), str(msg), str(category)))
        if ran:
            _write_state()
    for type_, msg, category in raised:
        try:
            _notify(type_, msg, category)
        except Exception:
            logger.exception("Failed to raise a monitor notification")
    return raised


def _acquire_lock() -> bool:
    global _lock_fh
    if _lock_fh is not None:
        return True
    if fcntl is None:
        return True
    fh = None
    try:
        fh = open(_lock_path(), 'a+')
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError):
        if fh is not None:
            try:
                fh.close()
            except Exception:
                pass
        return False
    _lock_fh = fh
    return True


def _release_lock():
    global _lock_fh
    fh, _lock_fh = _lock_fh, None
    if fh is None:
        return
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        fh.close()
    except Exception:
        pass


def _loop():
    while not _stop_event.is_set():
        try:
            run_checks_once()
        except Exception:
            logger.exception("Monitor cycle failed")
        _stop_event.wait(LOOP_TICK)


def start() -> bool:
    """Become the single runner and start the check loop.

    Returns False when another worker already holds the runner lock.
    """
    global _thread
    if _thread is not None and _thread.is_alive():
        return True
    if not _acquire_lock():
        return False
    _stop_event.clear()
    _thread = threading.Thread(target=_loop, daemon=True)
    _thread.start()
    logger.info("Monitor started")
    return True


def stop():
    """Stop the check loop and release the runner lock."""
    global _thread
    _stop_event.set()
    thread, _thread = _thread, None
    if thread is not None and thread.is_alive():
        thread.join(timeout=5)
    _release_lock()


_checks = [
    ('agents',          AGENT_INTERVAL,    _check_agents),
    ('certs',           CERT_INTERVAL,     _check_certs),
    ('traefik',         TRAEFIK_INTERVAL,  _check_traefik),
    ('crowdsec_agents', CROWDSEC_INTERVAL, _check_crowdsec_agents),
    ('geoip',           GEOIP_INTERVAL,    _check_geoip),
]
