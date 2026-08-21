package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// Traefik normally carries the very connection the answer travels back on, so
// restarting it before replying loses the reply. The host then reports the
// agent as unreachable even though the restart worked.
func TestStaticRestartAnswersBeforeRestarting(t *testing.T) {
	restarted := make(chan time.Time, 1)
	docker := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == http.MethodGet && strings.HasSuffix(r.URL.Path, "/json"):
			w.WriteHeader(http.StatusOK)
			w.Write([]byte(`{"Id":"abc"}`))
		case r.Method == http.MethodPost && strings.HasSuffix(r.URL.Path, "/restart"):
			select {
			case restarted <- time.Now():
			default:
			}
			w.WriteHeader(http.StatusNoContent)
		default:
			w.WriteHeader(http.StatusNotFound)
		}
	}))
	defer docker.Close()

	a := &App{cfg: &Config{RestartMethod: "proxy", DockerHost: docker.URL, TraefikContainer: "traefik"}}

	rec := httptest.NewRecorder()
	a.staticRestartHandler(rec, httptest.NewRequest(http.MethodPost, "/api/static/restart", nil))
	answered := time.Now()

	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d: %s", rec.Code, rec.Body.String())
	}
	var body map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("response is not json: %v", err)
	}
	if body["ok"] != true || body["restarting"] != true {
		t.Fatalf("want ok+restarting, got %v", body)
	}

	select {
	case at := <-restarted:
		if !at.After(answered) {
			t.Fatal("the restart ran before the handler answered")
		}
	case <-time.After(5 * time.Second):
		t.Fatal("the restart never ran")
	}
}

// A container that does not exist is worth reporting synchronously: Traefik is
// still up, so the answer gets through.
func TestStaticRestartReportsMissingContainer(t *testing.T) {
	docker := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	defer docker.Close()

	a := &App{cfg: &Config{RestartMethod: "proxy", DockerHost: docker.URL, TraefikContainer: "nope"}}
	rec := httptest.NewRecorder()
	a.staticRestartHandler(rec, httptest.NewRequest(http.MethodPost, "/api/static/restart", nil))

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("want 500, got %d: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), "not found") {
		t.Fatalf("want the container name explained, got %s", rec.Body.String())
	}
}

func TestStaticRestartRejectsUnconfiguredMethod(t *testing.T) {
	a := &App{cfg: &Config{}}
	rec := httptest.NewRecorder()
	a.staticRestartHandler(rec, httptest.NewRequest(http.MethodPost, "/api/static/restart", nil))
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("want 400, got %d", rec.Code)
	}
}
