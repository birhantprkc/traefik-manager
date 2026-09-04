package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestEventLogKeepsOnlyTheMostRecentEntries(t *testing.T) {
	log := newEventLog()
	for i := 0; i < eventRingSize+25; i++ {
		log.record("git", "failure")
	}
	all := log.since(0)
	if len(all) != eventRingSize {
		t.Fatalf("ring should cap at %d, got %d", eventRingSize, len(all))
	}
	if all[0].ID != 26 {
		t.Fatalf("oldest surviving id should be 26, got %d", all[0].ID)
	}
}

func TestEventLogIdsAlwaysIncrease(t *testing.T) {
	log := newEventLog()
	for i := 0; i < 5; i++ {
		log.record("backup", "failure")
	}
	all := log.since(0)
	for i := 1; i < len(all); i++ {
		if all[i].ID <= all[i-1].ID {
			t.Fatalf("ids must increase: %d then %d", all[i-1].ID, all[i].ID)
		}
	}
}

func TestEventLogSinceReturnsOnlyNewer(t *testing.T) {
	log := newEventLog()
	log.record("git", "one")
	log.record("git", "two")
	log.record("git", "three")
	out := log.since(2)
	if len(out) != 1 || out[0].Message != "three" {
		t.Fatalf("since(2) should return only the third event, got %+v", out)
	}
	if len(log.since(99)) != 0 {
		t.Fatal("since past the end must be empty")
	}
}

func TestEventsHandlerReportsLatestSoTheHubCanResume(t *testing.T) {
	app := &App{cfg: &Config{}, events: newEventLog()}
	app.events.record("restart", "boom")
	app.events.record("restart", "boom again")

	req := httptest.NewRequest(http.MethodGet, "/api/events?since=1", nil)
	rec := httptest.NewRecorder()
	app.eventsHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("want 200, got %d", rec.Code)
	}
	var body struct {
		Events []Event `json:"events"`
		Latest int64   `json:"latest"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("bad json: %v", err)
	}
	if len(body.Events) != 1 || body.Events[0].Message != "boom again" {
		t.Fatalf("unexpected events %+v", body.Events)
	}
	if body.Latest != 2 {
		t.Fatalf("latest should be 2, got %d", body.Latest)
	}
}

func TestEventsHandlerRejectsABadCursor(t *testing.T) {
	app := &App{cfg: &Config{}, events: newEventLog()}
	req := httptest.NewRequest(http.MethodGet, "/api/events?since=abc", nil)
	rec := httptest.NewRecorder()
	app.eventsHandler(rec, req)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("want 400 for a non-numeric cursor, got %d", rec.Code)
	}
}

func TestFailurefRecordsAndStillLogs(t *testing.T) {
	app := &App{cfg: &Config{}, events: newEventLog()}
	app.failuref("git", "auto-push failed: %v", os.ErrPermission)
	all := app.events.since(0)
	if len(all) != 1 {
		t.Fatalf("want one recorded event, got %d", len(all))
	}
	if all[0].Kind != "git" {
		t.Fatalf("kind should be git, got %q", all[0].Kind)
	}
	if all[0].Message != "auto-push failed: permission denied" {
		t.Fatalf("unexpected message %q", all[0].Message)
	}
}

func TestUnwritableStorageIsReported(t *testing.T) {
	dir := t.TempDir()
	cfgDir := filepath.Join(dir, "config")
	if err := os.MkdirAll(cfgDir, 0o755); err != nil {
		t.Fatal(err)
	}
	cfg := &Config{ConfigPath: cfgDir, BackupDir: filepath.Join(dir, "backups")}

	if problems := unwritableStorage(cfg); len(problems) != 0 {
		t.Fatalf("a healthy setup should report nothing, got %+v", problems)
	}

	if err := os.Chmod(cfgDir, 0o500); err != nil {
		t.Fatal(err)
	}
	defer os.Chmod(cfgDir, 0o700)

	problems := unwritableStorage(cfg)
	if len(problems) != 1 || problems[0].Label != "Dynamic config" {
		t.Fatalf("want the dynamic config directory reported, got %+v", problems)
	}
	if problems[0].Err == "" {
		t.Fatal("the reason must be included")
	}
}

func TestStorageProbeLeavesNothingBehind(t *testing.T) {
	dir := t.TempDir()
	cfg := &Config{ConfigPath: dir, BackupDir: filepath.Join(dir, "backups")}
	unwritableStorage(cfg)
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatal(err)
	}
	for _, e := range entries {
		if len(e.Name()) > 5 && e.Name()[:5] == ".tma-" {
			t.Fatalf("probe file left behind: %s", e.Name())
		}
	}
}

func TestConfigWriteIsRefusedWhenTheBackupFails(t *testing.T) {
	dir := t.TempDir()
	cfgPath := filepath.Join(dir, "dynamic.yml")
	original := []byte("http:\n  routers: {}\n")
	if err := os.WriteFile(cfgPath, original, 0o600); err != nil {
		t.Fatal(err)
	}
	blocked := filepath.Join(dir, "blocked")
	if err := os.MkdirAll(blocked, 0o500); err != nil {
		t.Fatal(err)
	}
	defer os.Chmod(blocked, 0o700)

	app := &App{
		cfg:    &Config{ConfigPath: cfgPath, BackupDir: filepath.Join(blocked, "backups")},
		events: newEventLog(),
	}

	body := `{"content":"http:\n  routers: {overwritten: {}}\n"}`
	req := httptest.NewRequest(http.MethodPost, "/api/configs", strings.NewReader(body))
	rec := httptest.NewRecorder()
	app.configsWriteHandler(rec, req)

	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("a failed backup must refuse the write, got %d", rec.Code)
	}
	after, err := os.ReadFile(cfgPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(after) != string(original) {
		t.Fatal("the config was overwritten even though the backup failed")
	}
	if len(app.events.since(0)) != 1 {
		t.Fatal("the failure must be recorded as an event")
	}
}
