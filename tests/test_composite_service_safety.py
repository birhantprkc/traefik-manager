import core.settings as settings_mod
from conftest import read_config, write_config, post_form


def _save_http(client, name, **extra):
    form = dict(serviceName=name, subdomain=f"{name}.example.com", protocol="http",
                scheme="http", targetIp="10.0.0.1", targetPort="8080",
                certResolver="letsencrypt")
    form.update(extra)
    return post_form(client, "/save", **form)


def _toggle(client, route_id, enable):
    return client.post(f"/api/routes/{route_id}/toggle", json={"enable": enable},
                       headers={"X-CSRF-Token": "testtoken", "X-Requested-With": "fetch"})


HAND_WRITTEN_WEIGHTED = """
http:
  routers:
    api-blue:
      rule: Host(`blue.example.com`)
      service: api-blue-service
      entryPoints: [https]
  services:
    api-blue-service:
      loadBalancer:
        servers:
          - url: http://10.0.0.1:8080
    api-pool:
      weighted:
        services:
          - name: api-blue-service
            weight: 3
          - name: api-green-service
"""


def test_deleting_a_route_keeps_a_service_a_weighted_pool_references(client):
    """The pool's child must survive, even though no router points at it."""
    write_config(HAND_WRITTEN_WEIGHTED)
    r = client.post("/delete/api-blue", headers={"X-CSRF-Token": "testtoken",
                                                 "X-Requested-With": "fetch"})
    assert r.status_code < 400, r.get_data(as_text=True)
    svcs = read_config()["http"]["services"]
    assert "api-blue-service" in svcs, "the weighted pool still references it"
    assert "api-pool" in svcs


def test_disabling_a_route_keeps_a_service_a_weighted_pool_references(client):
    write_config(HAND_WRITTEN_WEIGHTED)
    assert _toggle(client, "api-blue", False).status_code < 400
    svcs = read_config().get("http", {}).get("services", {})
    assert "api-blue-service" in svcs


def test_mirroring_and_failover_children_are_protected(client):
    write_config("""
http:
  routers:
    r-primary:
      rule: Host(`p.example.com`)
      service: primary-service
    r-shadow:
      rule: Host(`s.example.com`)
      service: shadow-service
  services:
    primary-service:
      loadBalancer:
        servers: [{url: 'http://10.0.0.1:80'}]
    shadow-service:
      loadBalancer:
        servers: [{url: 'http://10.0.0.2:80'}]
    mir:
      mirroring:
        service: primary-service
        mirrors:
          - name: shadow-service
            percent: 10
    fo:
      failover:
        service: primary-service
        fallback: shadow-service
""")
    for rid in ("r-primary", "r-shadow"):
        assert client.post(f"/delete/{rid}", headers={"X-CSRF-Token": "testtoken",
                                                      "X-Requested-With": "fetch"}).status_code < 400
    svcs = read_config()["http"]["services"]
    assert "primary-service" in svcs, "mirroring.service and failover.service reference it"
    assert "shadow-service" in svcs, "mirrors[].name and failover.fallback reference it"


def test_a_disabled_route_protects_its_service_from_another_routes_delete(client):
    """A disabled route's snapshot can hold the only remaining reference."""
    _save_http(client, "shared1")
    r = post_form(client, "/save", serviceName="shared2",
                  subdomain="shared2.example.com", protocol="http", scheme="http",
                  targetIp="10.0.0.9", targetPort="8080", certResolver="letsencrypt",
                  serviceRef="shared1-service")
    assert r.status_code < 400, r.get_data(as_text=True)
    assert _toggle(client, "shared2", False).status_code < 400
    assert client.post("/delete/shared1", headers={"X-CSRF-Token": "testtoken",
                                                   "X-Requested-With": "fetch"}).status_code < 400
    svcs = read_config().get("http", {}).get("services", {})
    assert "shared1-service" in svcs, "the disabled route still references it"


def test_a_service_does_not_protect_itself(client):
    """A self-referencing composite must not become undeletable."""
    write_config("""
http:
  routers:
    solo:
      rule: Host(`solo.example.com`)
      service: solo-service
  services:
    solo-service:
      weighted:
        services:
          - name: solo-service
""")
    assert client.post("/delete/solo", headers={"X-CSRF-Token": "testtoken",
                                                "X-Requested-With": "fetch"}).status_code < 400
    assert "solo-service" not in read_config().get("http", {}).get("services", {})


def test_editing_a_disabled_route_does_not_500(client):
    _save_http(client, "dis1")
    assert _toggle(client, "dis1", False).status_code < 400
    assert "dis1" in settings_mod.load_settings().get("disabled_routes", {})
    r = _save_http(client, "dis1", isEdit="true", originalId="dis1", targetPort="9090")
    assert r.status_code < 500, r.get_data(as_text=True)
    assert r.status_code < 400, r.get_data(as_text=True)


def test_highest_random_weight_is_reported_as_its_own_type(client):
    write_config("""
http:
  routers:
    hrw:
      rule: Host(`hrw.example.com`)
      service: hrw-service
  services:
    hrw-service:
      highestRandomWeight:
        services:
          - name: a-service
          - name: b-service
""")
    r = client.get("/api/routes")
    assert r.status_code == 200
    app = next(a for a in r.get_json()["apps"] if a["name"] == "hrw")
    assert app["serviceType"] == "highestRandomWeight", \
        "must not be reported as an editable loadBalancer"
