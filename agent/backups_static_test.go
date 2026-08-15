package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func newBackupApp(t *testing.T) (*App, string, string, string) {
	t.Helper()
	root := t.TempDir()
	dynDir := filepath.Join(root, "conf.d")
	staticPath := filepath.Join(root, "traefik.yml")
	os.MkdirAll(dynDir, 0o755)
	os.WriteFile(filepath.Join(dynDir, "dynamic.yml"), []byte("http: {}\n"), 0o644)
	os.WriteFile(staticPath, []byte("entryPoints:\n  web:\n    address: ':80'\n"), 0o644)
	a := &App{cfg: &Config{
		ConfigPath:       dynDir,
		StaticConfigPath: staticPath,
		BackupDir:        root,
	}}
	return a, root, dynDir, staticPath
}

func TestBackupListClassifiesStatic(t *testing.T) {
	a, root, _, _ := newBackupApp(t)
	bdir := filepath.Join(root, "backups")
	os.MkdirAll(bdir, 0o755)
	os.WriteFile(filepath.Join(bdir, "traefik.yml.20250101_000000.bak"), []byte("s"), 0o644)
	os.WriteFile(filepath.Join(bdir, "dynamic.yml.20250101_000000.bak"), []byte("d"), 0o644)

	rec := httptest.NewRecorder()
	a.backupsListHandler(rec, httptest.NewRequest(http.MethodGet, "/api/backups", nil))
	var resp struct {
		Backups []struct {
			Name string `json:"name"`
			Kind string `json:"kind"`
		} `json:"backups"`
		StaticConfigured bool `json:"static_configured"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &resp); err != nil {
		t.Fatal(err)
	}
	if !resp.StaticConfigured {
		t.Fatal("static_configured must be true when STATIC_CONFIG_PATH is set")
	}
	kinds := map[string]string{}
	for _, b := range resp.Backups {
		kinds[b.Name] = b.Kind
	}
	if kinds["traefik.yml.20250101_000000.bak"] != "static" {
		t.Fatalf("traefik.yml backup classified as %q, want static", kinds["traefik.yml.20250101_000000.bak"])
	}
	if kinds["dynamic.yml.20250101_000000.bak"] != "routes" {
		t.Fatalf("dynamic.yml backup classified as %q, want routes", kinds["dynamic.yml.20250101_000000.bak"])
	}
}

func TestRestoreStaticBackupWritesToStaticPath(t *testing.T) {
	a, root, dynDir, staticPath := newBackupApp(t)
	bdir := filepath.Join(root, "backups")
	os.MkdirAll(bdir, 0o755)
	restored := "entryPoints:\n  web:\n    address: ':8080'\n"
	os.WriteFile(filepath.Join(bdir, "traefik.yml.20250101_000000.bak"), []byte(restored), 0o644)

	rec := httptest.NewRecorder()
	a.restoreHandler(rec, httptest.NewRequest(http.MethodPost, "/api/restore/traefik.yml.20250101_000000.bak", nil))
	if rec.Code != 200 {
		t.Fatalf("restore returned %d: %s", rec.Code, rec.Body.String())
	}
	got, _ := os.ReadFile(staticPath)
	if string(got) != restored {
		t.Fatalf("static path not restored, content: %q", string(got))
	}
	if _, err := os.Stat(filepath.Join(dynDir, "traefik.yml")); err == nil {
		t.Fatal("static backup must not be written into the dynamic config directory")
	}
}

func TestRestoreDynamicBackupStillTargetsConfigDir(t *testing.T) {
	a, root, dynDir, staticPath := newBackupApp(t)
	bdir := filepath.Join(root, "backups")
	os.MkdirAll(bdir, 0o755)
	os.WriteFile(filepath.Join(bdir, "dynamic.yml.20250101_000000.bak"), []byte("tcp: {}\n"), 0o644)

	rec := httptest.NewRecorder()
	a.restoreHandler(rec, httptest.NewRequest(http.MethodPost, "/api/restore/dynamic.yml.20250101_000000.bak", nil))
	if rec.Code != 200 {
		t.Fatalf("restore returned %d: %s", rec.Code, rec.Body.String())
	}
	got, _ := os.ReadFile(filepath.Join(dynDir, "dynamic.yml"))
	if string(got) != "tcp: {}\n" {
		t.Fatalf("dynamic restore wrong content: %q", string(got))
	}
	static, _ := os.ReadFile(staticPath)
	if string(static) != "entryPoints:\n  web:\n    address: ':80'\n" {
		t.Fatal("dynamic restore must not touch the static file")
	}
}
