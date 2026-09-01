package main

import (
	"fmt"
	"os"
	"path/filepath"
)

type StorageProblem struct {
	Label string
	Path  string
	Err   string
}

func probeWritable(dir string) string {
	info, err := os.Stat(dir)
	if err != nil || !info.IsDir() {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return fmt.Sprintf("cannot be created: %v", err)
		}
	}
	probe := filepath.Join(dir, fmt.Sprintf(".tma-write-probe.%d", os.Getpid()))
	if err := os.WriteFile(probe, []byte("probe"), 0o600); err != nil {
		return err.Error()
	}
	os.Remove(probe)
	return ""
}

func storageDir(path string) string {
	if info, err := os.Stat(path); err == nil && info.IsDir() {
		return path
	}
	return filepath.Dir(path)
}

func unwritableStorage(cfg *Config) []StorageProblem {
	targets := []struct{ label, path string }{
		{"Dynamic config", storageDir(cfg.ConfigPath)},
		{"Backups", cfg.BackupDir},
	}
	if cfg.StaticConfigPath != "" {
		targets = append(targets, struct{ label, path string }{
			"Static config", storageDir(cfg.StaticConfigPath)})
	}
	seen := map[string]bool{}
	out := []StorageProblem{}
	for _, t := range targets {
		abs, err := filepath.Abs(t.path)
		if err != nil {
			abs = t.path
		}
		if seen[abs] {
			continue
		}
		seen[abs] = true
		if msg := probeWritable(abs); msg != "" {
			out = append(out, StorageProblem{Label: t.label, Path: abs, Err: msg})
		}
	}
	return out
}
