package codex

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenhg5/cc-connect/core"
)

func TestAgentSessionFilesUseActiveProviderCodexHome(t *testing.T) {
	workDir := t.TempDir()
	codexHome := filepath.Join(t.TempDir(), ".codex-active")
	sessionsDir := filepath.Join(codexHome, "sessions")
	if err := os.MkdirAll(sessionsDir, 0o755); err != nil {
		t.Fatalf("mkdir sessions: %v", err)
	}

	sessionID := "test-session-provider-home"
	transcriptPath := filepath.Join(sessionsDir, "rollout-"+sessionID+".jsonl")
	transcript := strings.Join([]string{
		`{"timestamp":"2026-01-01T00:00:00Z","type":"session_meta","payload":{"id":"` + sessionID + `","source":"exec","originator":"codex_exec","cwd":"` + workDir + `"}}`,
		`{"timestamp":"2026-01-01T00:00:01Z","type":"response_item","payload":{"role":"user","content":[{"type":"input_text","text":"hello from feishu"}]}}`,
		`{"timestamp":"2026-01-01T00:00:02Z","type":"response_item","payload":{"role":"assistant","content":[{"type":"output_text","text":"hi there"}]}}`,
		"",
	}, "\n")
	if err := os.WriteFile(transcriptPath, []byte(transcript), 0o644); err != nil {
		t.Fatalf("write transcript: %v", err)
	}

	t.Setenv("CODEX_HOME", filepath.Join(t.TempDir(), ".wrong-default"))

	agent := &Agent{
		workDir: workDir,
		providers: []core.ProviderConfig{
			{
				Name: "primary",
				Env:  map[string]string{"CODEX_HOME": codexHome},
			},
		},
		activeIdx: 0,
	}

	sessions, err := agent.ListSessions(context.Background())
	if err != nil {
		t.Fatalf("ListSessions: %v", err)
	}
	if len(sessions) != 1 || sessions[0].ID != sessionID {
		t.Fatalf("sessions = %v, want session %q from provider CODEX_HOME", sessions, sessionID)
	}

	history, err := agent.GetSessionHistory(context.Background(), sessionID, 0)
	if err != nil {
		t.Fatalf("GetSessionHistory: %v", err)
	}
	if len(history) != 2 || history[0].Content != "hello from feishu" || history[1].Content != "hi there" {
		t.Fatalf("history = %v, want user/assistant entries from provider CODEX_HOME", history)
	}

	data, err := os.ReadFile(transcriptPath)
	if err != nil {
		t.Fatalf("read transcript: %v", err)
	}
	if !strings.Contains(string(data), `"source":"cli"`) {
		t.Fatalf("expected transcript to be patched for CLI resume visibility, got: %s", string(data))
	}

	if err := agent.DeleteSession(context.Background(), sessionID); err != nil {
		t.Fatalf("DeleteSession: %v", err)
	}
	if _, err := os.Stat(transcriptPath); !os.IsNotExist(err) {
		t.Fatalf("expected transcript to be deleted, stat err=%v", err)
	}
}

func TestAgentSessionFilesSpanAllConfiguredProviderHomes(t *testing.T) {
	workDir := t.TempDir()
	homeA := filepath.Join(t.TempDir(), ".codex-a")
	homeB := filepath.Join(t.TempDir(), ".codex-b")
	for _, item := range []struct {
		home       string
		sessionID  string
		userText   string
		assistText string
	}{
		{home: homeA, sessionID: "session-a", userText: "from a", assistText: "reply a"},
		{home: homeB, sessionID: "session-b", userText: "from b", assistText: "reply b"},
	} {
		sessionsDir := filepath.Join(item.home, "sessions")
		if err := os.MkdirAll(sessionsDir, 0o755); err != nil {
			t.Fatalf("mkdir sessions: %v", err)
		}
		transcriptPath := filepath.Join(sessionsDir, "rollout-"+item.sessionID+".jsonl")
		transcript := strings.Join([]string{
			`{"timestamp":"2026-01-01T00:00:00Z","type":"session_meta","payload":{"id":"` + item.sessionID + `","source":"exec","originator":"codex_exec","cwd":"` + workDir + `"}}`,
			`{"timestamp":"2026-01-01T00:00:01Z","type":"response_item","payload":{"role":"user","content":[{"type":"input_text","text":"` + item.userText + `"}]}}`,
			`{"timestamp":"2026-01-01T00:00:02Z","type":"response_item","payload":{"role":"assistant","content":[{"type":"output_text","text":"` + item.assistText + `"}]}}`,
			"",
		}, "\n")
		if err := os.WriteFile(transcriptPath, []byte(transcript), 0o644); err != nil {
			t.Fatalf("write transcript: %v", err)
		}
	}

	agent := &Agent{
		workDir: workDir,
		providers: []core.ProviderConfig{
			{Name: "primary", Env: map[string]string{"CODEX_HOME": homeA}},
			{Name: "secondary", Env: map[string]string{"CODEX_HOME": homeB}},
		},
		activeIdx: 1,
	}

	sessions, err := agent.ListSessions(context.Background())
	if err != nil {
		t.Fatalf("ListSessions: %v", err)
	}
	if len(sessions) != 2 {
		t.Fatalf("sessions = %v, want 2 sessions across provider homes", sessions)
	}

	gotProviders := map[string]string{}
	for _, session := range sessions {
		gotProviders[session.ID] = session.ProviderName
	}
	if gotProviders["session-a"] != "primary" || gotProviders["session-b"] != "secondary" {
		t.Fatalf("provider mapping = %v, want session-a->primary and session-b->secondary", gotProviders)
	}

	historyA, err := agent.GetSessionHistory(context.Background(), "session-a", 0)
	if err != nil {
		t.Fatalf("GetSessionHistory(session-a): %v", err)
	}
	if len(historyA) != 2 || historyA[0].Content != "from a" || historyA[1].Content != "reply a" {
		t.Fatalf("historyA = %v, want entries from inactive provider home", historyA)
	}

	if err := agent.DeleteSession(context.Background(), "session-a"); err != nil {
		t.Fatalf("DeleteSession(session-a): %v", err)
	}
	if _, err := os.Stat(filepath.Join(homeA, "sessions", "rollout-session-a.jsonl")); !os.IsNotExist(err) {
		t.Fatalf("expected inactive-provider transcript deleted, stat err=%v", err)
	}
}

func TestAgentStartSessionSyncsLatestTranscriptIntoActiveProviderHome(t *testing.T) {
	workDir := t.TempDir()
	homeA := filepath.Join(t.TempDir(), ".codex-a")
	homeB := filepath.Join(t.TempDir(), ".codex-b")
	sessionID := "shared-session"

	pathA := writeCodexTranscript(t, homeA, sessionID, workDir, "hello from a", "reply from a")
	pathB := writeCodexTranscript(t, homeB, sessionID, workDir, "stale hello", "stale reply")
	setFileModTime(t, pathB, time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC))
	setFileModTime(t, pathA, time.Date(2026, 1, 2, 0, 0, 0, 0, time.UTC))

	agent := &Agent{
		workDir: workDir,
		providers: []core.ProviderConfig{
			{Name: "primary", Env: map[string]string{"CODEX_HOME": homeA}},
			{Name: "secondary", Env: map[string]string{"CODEX_HOME": homeB}},
		},
		activeIdx: 1,
	}

	sess, err := agent.StartSession(context.Background(), sessionID)
	if err != nil {
		t.Fatalf("StartSession: %v", err)
	}
	defer sess.Close()

	targetPath := findSessionFile(sessionID, []sessionHomeRef{{CodexHome: homeB}})
	data, err := os.ReadFile(targetPath)
	if err != nil {
		t.Fatalf("read synced transcript: %v", err)
	}
	text := string(data)
	if !strings.Contains(text, "reply from a") {
		t.Fatalf("expected active home transcript to be refreshed from latest copy, got: %s", text)
	}
	if !strings.Contains(text, `"source":"cli"`) {
		t.Fatalf("expected synced transcript to be patched for CLI resume visibility, got: %s", text)
	}
}

func TestAgentSessionFilesDeduplicateAndPreferLatestTranscript(t *testing.T) {
	workDir := t.TempDir()
	homeA := filepath.Join(t.TempDir(), ".codex-a")
	homeB := filepath.Join(t.TempDir(), ".codex-b")
	sessionID := "shared-session"

	pathA := writeCodexTranscript(t, homeA, sessionID, workDir, "hello from a", "reply from a")
	pathB := writeCodexTranscript(t, homeB, sessionID, workDir, "hello from b", "reply from b")
	setFileModTime(t, pathA, time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC))
	setFileModTime(t, pathB, time.Date(2026, 1, 3, 0, 0, 0, 0, time.UTC))

	agent := &Agent{
		workDir: workDir,
		providers: []core.ProviderConfig{
			{Name: "primary", Env: map[string]string{"CODEX_HOME": homeA}},
			{Name: "secondary", Env: map[string]string{"CODEX_HOME": homeB}},
		},
		activeIdx: 0,
	}

	sessions, err := agent.ListSessions(context.Background())
	if err != nil {
		t.Fatalf("ListSessions: %v", err)
	}
	if len(sessions) != 1 {
		t.Fatalf("sessions = %v, want one deduplicated shared session", sessions)
	}
	if sessions[0].ProviderName != "secondary" {
		t.Fatalf("provider = %q, want secondary because it has the latest transcript", sessions[0].ProviderName)
	}

	history, err := agent.GetSessionHistory(context.Background(), sessionID, 0)
	if err != nil {
		t.Fatalf("GetSessionHistory: %v", err)
	}
	if len(history) != 2 || history[0].Content != "hello from b" || history[1].Content != "reply from b" {
		t.Fatalf("history = %v, want entries from latest transcript copy", history)
	}

	if err := agent.DeleteSession(context.Background(), sessionID); err != nil {
		t.Fatalf("DeleteSession: %v", err)
	}
	if _, err := os.Stat(pathA); !os.IsNotExist(err) {
		t.Fatalf("expected primary transcript deleted, stat err=%v", err)
	}
	if _, err := os.Stat(pathB); !os.IsNotExist(err) {
		t.Fatalf("expected secondary transcript deleted, stat err=%v", err)
	}
}

func TestAgentPrepareInteractiveSessionCatalogSyncsWorkspaceSessionsIntoActiveHome(t *testing.T) {
	workDir := t.TempDir()
	homeA := filepath.Join(t.TempDir(), ".codex-a")
	homeB := filepath.Join(t.TempDir(), ".codex-b")

	writeCodexTranscript(t, homeA, "session-a", workDir, "from a", "reply a")
	writeCodexTranscript(t, homeB, "session-b", workDir, "from b", "reply b")

	agent := &Agent{
		workDir: workDir,
		providers: []core.ProviderConfig{
			{Name: "primary", Env: map[string]string{"CODEX_HOME": homeA}},
			{Name: "secondary", Env: map[string]string{"CODEX_HOME": homeB}},
		},
		activeIdx: 1,
	}

	if err := agent.PrepareInteractiveSessionCatalog(context.Background()); err != nil {
		t.Fatalf("PrepareInteractiveSessionCatalog: %v", err)
	}

	targetPath := findSessionFile("session-a", []sessionHomeRef{{CodexHome: homeB}})
	if targetPath == "" {
		t.Fatal("expected session-a transcript to be mirrored into active provider home")
	}
	data, err := os.ReadFile(targetPath)
	if err != nil {
		t.Fatalf("read mirrored transcript: %v", err)
	}
	if !strings.Contains(string(data), `"source":"cli"`) {
		t.Fatalf("expected mirrored transcript to be patched for CLI resume visibility, got: %s", string(data))
	}
}

func writeCodexTranscript(t *testing.T, codexHome, sessionID, workDir, userText, assistantText string) string {
	t.Helper()

	sessionsDir := filepath.Join(codexHome, "sessions")
	if err := os.MkdirAll(sessionsDir, 0o755); err != nil {
		t.Fatalf("mkdir sessions: %v", err)
	}

	transcriptPath := filepath.Join(sessionsDir, "rollout-"+sessionID+".jsonl")
	transcript := strings.Join([]string{
		`{"timestamp":"2026-01-01T00:00:00Z","type":"session_meta","payload":{"id":"` + sessionID + `","source":"exec","originator":"codex_exec","cwd":"` + workDir + `"}}`,
		`{"timestamp":"2026-01-01T00:00:01Z","type":"response_item","payload":{"role":"user","content":[{"type":"input_text","text":"` + userText + `"}]}}`,
		`{"timestamp":"2026-01-01T00:00:02Z","type":"response_item","payload":{"role":"assistant","content":[{"type":"output_text","text":"` + assistantText + `"}]}}`,
		"",
	}, "\n")
	if err := os.WriteFile(transcriptPath, []byte(transcript), 0o644); err != nil {
		t.Fatalf("write transcript: %v", err)
	}
	return transcriptPath
}

func setFileModTime(t *testing.T, path string, ts time.Time) {
	t.Helper()
	if err := os.Chtimes(path, ts, ts); err != nil {
		t.Fatalf("chtimes %s: %v", path, err)
	}
}
