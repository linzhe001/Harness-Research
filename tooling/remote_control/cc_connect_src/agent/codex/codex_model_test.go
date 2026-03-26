package codex

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/chenhg5/cc-connect/core"
)

func TestConfiguredModels_BoundaryConditions(t *testing.T) {
	a := &Agent{
		providers: []core.ProviderConfig{
			{Models: []core.ModelOption{{Name: "first"}}},
			{Models: []core.ModelOption{{Name: "second"}}},
		},
	}

	tests := []struct {
		name      string
		activeIdx int
		wantNil   bool
		wantName  string
	}{
		{name: "negative index", activeIdx: -1, wantNil: true},
		{name: "out of range", activeIdx: 2, wantNil: true},
		{name: "valid index", activeIdx: 1, wantName: "second"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			a.activeIdx = tt.activeIdx
			got := a.configuredModels()
			if tt.wantNil {
				if got != nil {
					t.Fatalf("configuredModels() = %v, want nil", got)
				}
				return
			}
			if len(got) != 1 || got[0].Name != tt.wantName {
				t.Fatalf("configuredModels() = %v, want %q", got, tt.wantName)
			}
		})
	}
}

func TestChoosePreferredModel(t *testing.T) {
	models := []core.ModelOption{
		{Name: "gpt-5.3-codex"},
		{Name: "o3"},
	}

	if got := choosePreferredModel(models, []string{"gpt-5.4", "gpt-5.3-codex", "o3"}); got != "gpt-5.3-codex" {
		t.Fatalf("choosePreferredModel() = %q, want gpt-5.3-codex", got)
	}
	if got := choosePreferredModel(models, []string{"does-not-exist"}); got != "gpt-5.3-codex" {
		t.Fatalf("choosePreferredModel() fallback = %q, want first available", got)
	}
}

func TestNew_DefaultsToXHighAndPreferredModels(t *testing.T) {
	workDir := t.TempDir()
	binDir := filepath.Join(workDir, "bin")
	if err := os.MkdirAll(binDir, 0o755); err != nil {
		t.Fatalf("mkdir bin: %v", err)
	}
	scriptPath := filepath.Join(binDir, "codex")
	if err := os.WriteFile(scriptPath, []byte("#!/bin/sh\nexit 0\n"), 0o755); err != nil {
		t.Fatalf("write fake codex: %v", err)
	}
	t.Setenv("PATH", binDir+string(os.PathListSeparator)+os.Getenv("PATH"))

	agentRaw, err := New(map[string]any{"work_dir": workDir})
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	agent := agentRaw.(*Agent)
	if agent.reasoningEffort != "xhigh" {
		t.Fatalf("reasoningEffort = %q, want xhigh", agent.reasoningEffort)
	}
	if len(agent.preferredModels) == 0 || agent.preferredModels[0] != "gpt-5.4" {
		t.Fatalf("preferredModels = %v, want default gpt-5.4 chain", agent.preferredModels)
	}
}
