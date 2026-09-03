package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"sync"
	"sync/atomic"
	"testing"
)

func csBodyServer(t *testing.T, acceptFrom int32) (*httptest.Server, *int32, *[]string) {
	t.Helper()
	var calls int32
	var mu sync.Mutex
	bodies := []string{}
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/v1/watchers/login" {
			json.NewEncoder(w).Encode(map[string]any{
				"token": "tok", "expire": "2099-01-01T00:00:00Z"})
			return
		}
		raw, _ := io.ReadAll(r.Body)
		mu.Lock()
		bodies = append(bodies, string(raw))
		mu.Unlock()
		if atomic.AddInt32(&calls, 1) < acceptFrom {
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte(`{"code":401,"message":"signature is invalid"}`))
			return
		}
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"ok":true}`))
	}))
	t.Cleanup(srv.Close)
	return srv, &calls, &bodies
}

func TestARefusedTokenIsRetriedForARequestWithABody(t *testing.T) {
	srv, calls, bodies := csBodyServer(t, 2)
	csJWTReset()
	payload := `[{"decisions":[{"value":"1.2.3.4"}]}]`

	resp, err := csTokenApp(srv.URL).csRequest(context.Background(), http.MethodPost,
		"/v1/alerts", bytes.NewReader([]byte(payload)), true)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Fatalf("want 200 after the retry, got %d - adding a decision fails until the cached token expires", resp.StatusCode)
	}
	if *calls != 2 {
		t.Fatalf("want exactly one retry, got %d calls", *calls)
	}
	for i, b := range *bodies {
		if b != payload {
			t.Fatalf("attempt %d sent %q, want the original body replayed", i+1, b)
		}
	}
}

func TestADeleteWithAnEmptyBodyIsStillRetried(t *testing.T) {
	srv, calls, _ := csBodyServer(t, 2)
	csJWTReset()

	resp, err := csTokenApp(srv.URL).csRequest(context.Background(), http.MethodDelete,
		"/v1/decisions/7", http.NoBody, true)
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
}

func TestASecondRefusalIsNotRetriedAgain(t *testing.T) {
	srv, calls, _ := csBodyServer(t, 99)
	csJWTReset()

	resp, err := csTokenApp(srv.URL).csRequest(context.Background(), http.MethodPost,
		"/v1/alerts", bytes.NewReader([]byte(`[]`)), true)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusUnauthorized {
		t.Fatalf("want the 401 surfaced, got %d", resp.StatusCode)
	}
	if *calls != 2 {
		t.Fatalf("want exactly one retry then give up, got %d calls", *calls)
	}
}
