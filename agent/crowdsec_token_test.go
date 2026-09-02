package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync/atomic"
	"testing"
)

func csTokenServer(t *testing.T, acceptFrom int32) (*httptest.Server, *int32, *int32) {
	t.Helper()
	var logins, calls int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v1/watchers/login" {
			n := atomic.AddInt32(&logins, 1)
			json.NewEncoder(w).Encode(map[string]any{
				"token":  "token-" + string(rune('0'+n)),
				"expire": "2099-01-01T00:00:00Z",
			})
			return
		}
		n := atomic.AddInt32(&calls, 1)
		if n < acceptFrom {
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte(`{"code":401,"message":"signature is invalid"}`))
			return
		}
		json.NewEncoder(w).Encode([]map[string]any{{"id": 1}})
	}))
	return srv, &logins, &calls
}

func csTokenApp(url string) *App {
	return &App{cfg: &Config{
		CrowdSecLAPIURL:         url,
		CrowdSecMachineID:       "m",
		CrowdSecMachinePassword: "p",
		CrowdSecReadTimeout:     5,
	}}
}

func TestARefusedMachineTokenIsRetriedOnce(t *testing.T) {
	srv, logins, calls := csTokenServer(t, 2)
	defer srv.Close()
	csJWTReset()

	resp, err := csTokenApp(srv.URL).csRequest(context.Background(), http.MethodGet, "/v1/alerts", nil, true)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200 after the retry, got %d", resp.StatusCode)
	}
	if *calls != 2 {
		t.Fatalf("want exactly one retry, got %d calls", *calls)
	}
	if *logins != 2 {
		t.Fatalf("the retry must log in again, got %d logins", *logins)
	}
}

func TestAWorkingTokenIsReused(t *testing.T) {
	srv, logins, _ := csTokenServer(t, 1)
	defer srv.Close()
	csJWTReset()

	app := csTokenApp(srv.URL)
	for i := 0; i < 3; i++ {
		resp, err := app.csRequest(context.Background(), http.MethodGet, "/v1/alerts", nil, true)
		if err != nil {
			t.Fatal(err)
		}
		resp.Body.Close()
	}
	if *logins != 1 {
		t.Fatalf("the token cache must still work, got %d logins", *logins)
	}
}

func TestASecondRefusalIsNotRetriedForever(t *testing.T) {
	srv, _, calls := csTokenServer(t, 99)
	defer srv.Close()
	csJWTReset()

	resp, err := csTokenApp(srv.URL).csRequest(context.Background(), http.MethodGet, "/v1/alerts", nil, true)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("want the second 401 returned, got %d", resp.StatusCode)
	}
	if *calls != 2 {
		t.Fatalf("exactly one retry, never a loop: got %d calls", *calls)
	}
}

func TestARequestWithABodyIsNotRetried(t *testing.T) {
	srv, _, calls := csTokenServer(t, 99)
	defer srv.Close()
	csJWTReset()

	resp, err := csTokenApp(srv.URL).csRequest(context.Background(), http.MethodPost, "/v1/alerts",
		strings.NewReader(`[{"x":1}]`), true)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if *calls != 1 {
		t.Fatalf("a body is a one shot reader and cannot be replayed, got %d calls", *calls)
	}
}

func TestABouncerKeyRequestIsUnaffected(t *testing.T) {
	srv, logins, _ := csTokenServer(t, 1)
	defer srv.Close()
	csJWTReset()

	app := &App{cfg: &Config{CrowdSecLAPIURL: srv.URL, CrowdSecAPIKey: "k", CrowdSecReadTimeout: 5}}
	resp, err := app.csRequest(context.Background(), http.MethodGet, "/v1/decisions", nil, false)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if *logins != 0 {
		t.Fatalf("a bouncer key request must never log in, got %d logins", *logins)
	}
}

func TestCacheResetClearsEverything(t *testing.T) {
	csCache.mu.Lock()
	csCache.items = map[int64]json.RawMessage{1: json.RawMessage(`{"id":1}`)}
	csCache.ready = true
	csCache.mu.Unlock()

	csCacheReset()

	csCache.mu.Lock()
	defer csCache.mu.Unlock()
	if len(csCache.items) != 0 || csCache.ready {
		t.Fatal("a newly added decision stays invisible while a stale cache is served")
	}
	if !csCache.sync.IsZero() {
		t.Fatal("the sync stamp must be cleared too, or freshness is computed from an old read")
	}
}

func TestAddingADecisionResetsTheCache(t *testing.T) {
	src, err := os.ReadFile("handlers.go")
	if err != nil {
		t.Fatal(err)
	}
	body := string(src)
	i := strings.Index(body, "func (a *App) crowdsecAddDecisionHandler")
	if i < 0 {
		t.Fatal("the add handler moved")
	}
	end := strings.Index(body[i:], "\nfunc ")
	if !strings.Contains(body[i:i+end], "csCacheReset()") {
		t.Fatal("adding a decision must drop the cache, or the list shows the old one")
	}
}

func TestDeletingADecisionResetsTheCache(t *testing.T) {
	src, err := os.ReadFile("main.go")
	if err != nil {
		t.Fatal(err)
	}
	body := string(src)
	i := strings.Index(body, `"/api/crowdsec/decisions/"`)
	if i < 0 {
		t.Fatal("the delete route moved")
	}
	if !strings.Contains(body[i:i+300], "csCacheReset()") {
		t.Fatal("deleting a decision must drop the cache too")
	}
}
