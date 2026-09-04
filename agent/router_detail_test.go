package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func routerDetailStub(t *testing.T) (*App, *[]string) {
	t.Helper()
	var seen []string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		seen = append(seen, r.URL.Path)
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]any{
			"name":     "whoami@docker",
			"provider": "docker",
			"labels":   map[string]string{"traefik.enable": "true"},
		})
	}))
	t.Cleanup(srv.Close)
	return &App{cfg: &Config{TraefikAPIURL: srv.URL}, httpClient: srv.Client()}, &seen
}

func TestRouterDetailReachesTraefik(t *testing.T) {
	a, seen := routerDetailStub(t)
	w := httptest.NewRecorder()
	a.routerDetailHandler(w, httptest.NewRequest(http.MethodGet, "/", nil), "http/whoami@docker")

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	if len(*seen) != 1 || (*seen)[0] != "/api/http/routers/whoami@docker" {
		t.Fatalf("traefik path = %v, want /api/http/routers/whoami@docker", *seen)
	}
	var body map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("body is not json: %v", err)
	}
	if body["labels"] == nil {
		t.Fatal("labels were dropped, which is the whole point of this endpoint")
	}
}

func TestRouterDetailHonoursProtocol(t *testing.T) {
	for _, tc := range []struct{ in, want string }{
		{"tcp/db@file", "/api/tcp/routers/db@file"},
		{"udp/vpn@file", "/api/udp/routers/vpn@file"},
		{"HTTP/web@file", "/api/http/routers/web@file"},
		{"nonsense/web@file", "/api/http/routers/web@file"},
	} {
		a, seen := routerDetailStub(t)
		a.routerDetailHandler(httptest.NewRecorder(), httptest.NewRequest(http.MethodGet, "/", nil), tc.in)
		if len(*seen) != 1 || (*seen)[0] != tc.want {
			t.Errorf("%q -> %v, want %s", tc.in, *seen, tc.want)
		}
	}
}

func TestRouterDetailNeedsAName(t *testing.T) {
	for _, rest := range []string{"http", "http/", ""} {
		a, seen := routerDetailStub(t)
		w := httptest.NewRecorder()
		a.routerDetailHandler(w, httptest.NewRequest(http.MethodGet, "/", nil), rest)
		if w.Code != http.StatusBadRequest {
			t.Errorf("%q status = %d, want 400", rest, w.Code)
		}
		if len(*seen) != 0 {
			t.Errorf("%q reached traefik at %v", rest, *seen)
		}
	}
}
