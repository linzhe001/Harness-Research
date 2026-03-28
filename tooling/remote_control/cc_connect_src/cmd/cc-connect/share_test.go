package main

import (
	"reflect"
	"testing"
	"time"

	"github.com/chenhg5/cc-connect/core"
)

func TestNormalizeShareArgs(t *testing.T) {
	tests := []struct {
		name     string
		args     []string
		wantCmd  string
		wantArgs []string
	}{
		{name: "default auto", wantCmd: "auto"},
		{
			name:     "flags imply auto",
			args:     []string{"--account", "acc2"},
			wantCmd:  "auto",
			wantArgs: []string{"--account", "acc2"},
		},
		{
			name:     "slot shorthand implies use",
			args:     []string{"s003"},
			wantCmd:  "use",
			wantArgs: []string{"s003"},
		},
		{
			name:     "explicit next subcommand",
			args:     []string{"next"},
			wantCmd:  "next",
			wantArgs: []string{},
		},
		{
			name:     "explicit subcommand",
			args:     []string{"status", "s003"},
			wantCmd:  "status",
			wantArgs: []string{"s003"},
		},
		{
			name:     "freeform title becomes new",
			args:     []string{"train", "debug"},
			wantCmd:  "new",
			wantArgs: []string{"--title", "train debug"},
		},
		{name: "help passthrough", args: []string{"help"}, wantCmd: "help"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotCmd, gotArgs := normalizeShareArgs(tt.args)
			if gotCmd != tt.wantCmd {
				t.Fatalf("normalizeShareArgs(%v) cmd = %q, want %q", tt.args, gotCmd, tt.wantCmd)
			}
			if !reflect.DeepEqual(gotArgs, tt.wantArgs) {
				t.Fatalf("normalizeShareArgs(%v) args = %v, want %v", tt.args, gotArgs, tt.wantArgs)
			}
		})
	}
}

func TestReorderShareFlagArgs(t *testing.T) {
	got := reorderShareFlagArgs(
		[]string{"s003", "--account", "acc2", "--workspace", "/tmp/ws"},
		map[string]bool{
			"--account":   true,
			"--workspace": true,
		},
		nil,
	)
	want := []string{"--account", "acc2", "--workspace", "/tmp/ws", "s003"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("reorderShareFlagArgs = %v, want %v", got, want)
	}
}

func TestPickNextShareProviderPrefersNonCoolingProvider(t *testing.T) {
	now := time.Date(2026, 3, 28, 3, 30, 0, 0, time.UTC)
	providers := []core.ProviderConfig{
		{Name: "codex_primary", Priority: 100},
		{Name: "codex_secondary", Priority: 90},
		{Name: "codex_tertiary", Priority: 80},
	}
	cooldowns := map[string]time.Time{
		"codex_primary": now.Add(30 * time.Minute),
	}

	next := pickNextShareProvider(providers, "codex_secondary", cooldowns, now)
	if next == nil || next.Name != "codex_tertiary" {
		t.Fatalf("pickNextShareProvider = %+v, want codex_tertiary", next)
	}
}

func TestPickNextShareProviderFallsBackWhenAllCoolingDown(t *testing.T) {
	now := time.Date(2026, 3, 28, 3, 30, 0, 0, time.UTC)
	providers := []core.ProviderConfig{
		{Name: "codex_primary", Priority: 100},
		{Name: "codex_secondary", Priority: 90},
	}
	cooldowns := map[string]time.Time{
		"codex_primary": now.Add(30 * time.Minute),
	}

	next := pickNextShareProvider(providers, "codex_secondary", cooldowns, now)
	if next == nil || next.Name != "codex_primary" {
		t.Fatalf("pickNextShareProvider = %+v, want fallback codex_primary", next)
	}
}
