import core.agents_store as store
import core.settings as settings_mod


def _seed(agents):
    store.save_agents_file(agents)


def _put(client, agent_id, payload):
    import json
    return client.put(f"/api/agents/{agent_id}", data=json.dumps(payload),
                      content_type="application/json",
                      headers={"X-CSRF-Token": "testtoken", "X-Requested-With": "fetch"})


def test_renaming_into_another_agents_derived_branch_is_rejected(client):
    """Both agents derive their branch from their name, so the rename would collide.

    Two agents pushing to one branch reset --hard each other's config before
    committing, which destroys data inside the user's git repo.
    """
    _seed([
        {"id": "a1", "name": "alpha", "url": "http://a1:8090", "api_key": "k1",
         "git_host_backup": True, "git_host_branch": ""},
        {"id": "a2", "name": "beta", "url": "http://a2:8090", "api_key": "k2",
         "git_host_backup": True, "git_host_branch": ""},
    ])
    r = _put(client, "a2", {"name": "alpha"})
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "already used by" in r.get_json()["error"]
    assert store.load_agents()[1]["name"] == "beta", "the rename must not have landed"


def test_renaming_into_the_host_branch_is_rejected(client):
    s = settings_mod.load_settings()
    host_branch = s.get("git_backup_branch") or "main"
    _seed([{"id": "a1", "name": "alpha", "url": "http://a1:8090", "api_key": "k1",
            "git_host_backup": True, "git_host_branch": ""}])
    r = _put(client, "a1", {"name": host_branch})
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "used by the Host" in r.get_json()["error"]


def test_a_harmless_rename_still_works(client):
    _seed([{"id": "a1", "name": "alpha", "url": "http://a1:8090", "api_key": "k1",
            "git_host_backup": True, "git_host_branch": ""}])
    r = _put(client, "a1", {"name": "gamma"})
    assert r.status_code < 400, r.get_data(as_text=True)
    assert store.load_agents()[0]["name"] == "gamma"


def test_rename_is_unguarded_when_the_agent_pins_an_explicit_branch(client):
    """An explicit git_host_branch does not move when the name changes."""
    _seed([
        {"id": "a1", "name": "alpha", "url": "http://a1:8090", "api_key": "k1",
         "git_host_backup": True, "git_host_branch": "pinned-one"},
        {"id": "a2", "name": "beta", "url": "http://a2:8090", "api_key": "k2",
         "git_host_backup": True, "git_host_branch": "pinned-two"},
    ])
    r = _put(client, "a2", {"name": "alpha"})
    assert r.status_code < 400, r.get_data(as_text=True)
    assert store.load_agents()[1]["git_host_branch"] == "pinned-two"


def test_rename_is_unguarded_when_git_host_backup_is_off(client):
    _seed([
        {"id": "a1", "name": "alpha", "url": "http://a1:8090", "api_key": "k1",
         "git_host_backup": True, "git_host_branch": ""},
        {"id": "a2", "name": "beta", "url": "http://a2:8090", "api_key": "k2",
         "git_host_backup": False, "git_host_branch": ""},
    ])
    r = _put(client, "a2", {"name": "alpha"})
    assert r.status_code < 400, r.get_data(as_text=True)
    assert store.load_agents()[1]["name"] == "alpha"
