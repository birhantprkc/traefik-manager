package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"testing"
)

type authSink struct {
	mu   sync.Mutex
	seen []string
	srv  *httptest.Server
}

func newAuthSink(t *testing.T) *authSink {
	t.Helper()
	s := &authSink{}
	s.srv = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if a := r.Header.Get("Authorization"); a != "" {
			s.mu.Lock()
			s.seen = append(s.seen, a)
			s.mu.Unlock()
			w.WriteHeader(http.StatusOK)
			return
		}
		w.Header().Set("WWW-Authenticate", `Basic realm="git"`)
		w.WriteHeader(http.StatusUnauthorized)
	}))
	t.Cleanup(s.srv.Close)
	return s
}

func (s *authSink) captured() []string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return append([]string(nil), s.seen...)
}

func gitTestApp(t *testing.T, configuredRepo string) *App {
	t.Helper()
	dir := t.TempDir()
	return &App{cfg: &Config{
		BackupDir:         dir,
		GitBackupRepo:     configuredRepo,
		GitBackupUsername: "operator",
		GitBackupToken:    "ghp_OPERATOR_SECRET_PAT",
	}}
}

func postGitTest(a *App, body map[string]string) *httptest.ResponseRecorder {
	buf, _ := json.Marshal(body)
	r := httptest.NewRequest(http.MethodPost, "/api/backup/git/test", bytes.NewReader(buf))
	w := httptest.NewRecorder()
	a.gitTestHandler(w, r)
	return w
}

func TestGitTestDoesNotSendTheStoredTokenToAnotherHost(t *testing.T) {
	if _, err := os.Stat("/usr/bin/git"); err != nil {
		t.Skip("git not available")
	}
	sink := newAuthSink(t)
	a := gitTestApp(t, "https://github.com/operator/config.git")

	postGitTest(a, map[string]string{"repo_url": sink.srv.URL + "/attacker.git"})

	if got := sink.captured(); len(got) > 0 {
		t.Fatalf("the stored git token was sent to an attacker-chosen host: %v", got)
	}
}

func TestGitTestStillUsesTheStoredTokenForTheConfiguredRepo(t *testing.T) {
	if _, err := os.Stat("/usr/bin/git"); err != nil {
		t.Skip("git not available")
	}
	sink := newAuthSink(t)
	a := gitTestApp(t, sink.srv.URL+"/config.git")

	postGitTest(a, nil)

	got := sink.captured()
	if len(got) == 0 {
		t.Fatal("testing the configured repo must still authenticate, or the button is useless")
	}
	if !strings.HasPrefix(got[0], "Basic ") {
		t.Fatalf("unexpected auth form: %q", got[0])
	}
}

func TestGitTestUsesACallerSuppliedTokenForACallerSuppliedRepo(t *testing.T) {
	if _, err := os.Stat("/usr/bin/git"); err != nil {
		t.Skip("git not available")
	}
	sink := newAuthSink(t)
	a := gitTestApp(t, "https://github.com/operator/config.git")

	postGitTest(a, map[string]string{
		"repo_url": sink.srv.URL + "/new.git",
		"username": "someone",
		"token":    "ghp_THE_USER_JUST_TYPED_THIS",
	})

	got := sink.captured()
	if len(got) == 0 {
		t.Fatal("a user testing new credentials must still be able to")
	}
}
