package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"github.com/chenhg5/cc-connect/config"
	"github.com/chenhg5/cc-connect/core"
)

type shareProjectRuntime struct {
	dataDir         string
	projectName     string
	workspace       string
	agent           core.Agent
	mode            string
	model           string
	reasoningEffort string
}

type interactiveSessionCatalogPreparer interface {
	PrepareInteractiveSessionCatalog(context.Context) error
}

type localShareMonitor struct {
	runtime      *shareProjectRuntime
	manager      *core.SharedSlotManager
	workspace    string
	slot         string
	holderID     string
	before       map[string]time.Time
	sessionID    string
	lastObserved time.Time
	startedAt    time.Time
}

type localProviderCooldownState struct {
	Providers map[string]time.Time `json:"providers"`
}

func formatShareCLILease(lease *core.SharedSlotLease, now time.Time) string {
	if lease == nil {
		return "free"
	}
	holder := strings.TrimSpace(lease.HolderName)
	if holder == "" {
		holder = strings.TrimSpace(lease.HolderID)
	}
	if holder == "" {
		holder = lease.HolderType
	}
	remaining := lease.LeaseUntil.Sub(now).Round(time.Minute)
	if remaining < 0 {
		remaining = 0
	}
	return fmt.Sprintf("%s until %s (%s remaining)", holder, lease.LeaseUntil.Format("2006-01-02 15:04"), remaining)
}

func formatShareCLIView(view core.SharedSlotView) string {
	parts := []string{view.Slot.Slot}
	if title := strings.TrimSpace(view.Slot.Title); title != "" {
		parts = append(parts, fmt.Sprintf("title=%s", title))
	}
	if sessionID := strings.TrimSpace(view.Slot.SessionID); sessionID != "" {
		shortID := sessionID
		if len(shortID) > 12 {
			shortID = shortID[:12]
		}
		parts = append(parts, fmt.Sprintf("session=%s", shortID))
	}
	if provider := strings.TrimSpace(view.Slot.ProviderName); provider != "" {
		parts = append(parts, fmt.Sprintf("provider=%s", provider))
	}
	parts = append(parts, fmt.Sprintf("lease=%s", formatShareCLILease(view.Lease, time.Now())))
	return "- " + strings.Join(parts, " | ")
}

func isSharedSlotID(raw string) bool {
	slot := strings.TrimSpace(raw)
	if len(slot) < 2 || slot[0] != 's' {
		return false
	}
	for _, ch := range slot[1:] {
		if ch < '0' || ch > '9' {
			return false
		}
	}
	return true
}

func normalizeShareArgs(args []string) (string, []string) {
	if len(args) == 0 {
		return "auto", nil
	}

	first := strings.TrimSpace(args[0])
	switch first {
	case "list", "new", "use", "next", "status", "release":
		return first, args[1:]
	case "help", "--help", "-h":
		return "help", nil
	}
	if strings.HasPrefix(first, "-") {
		return "auto", args
	}
	if isSharedSlotID(first) {
		return "use", args
	}
	title := strings.TrimSpace(strings.Join(args, " "))
	if title == "" {
		return "new", nil
	}
	return "new", []string{"--title", title}
}

func reorderShareFlagArgs(args []string, valueFlags, boolFlags map[string]bool) []string {
	if len(args) == 0 {
		return nil
	}

	options := make([]string, 0, len(args))
	positionals := make([]string, 0, len(args))
	for i := 0; i < len(args); i++ {
		arg := args[i]
		if arg == "--" {
			positionals = append(positionals, args[i+1:]...)
			break
		}
		if strings.HasPrefix(arg, "--") || strings.HasPrefix(arg, "-") {
			name := arg
			hasInlineValue := false
			if idx := strings.Index(arg, "="); idx >= 0 {
				name = arg[:idx]
				hasInlineValue = true
			}
			if boolFlags[name] {
				options = append(options, arg)
				continue
			}
			if valueFlags[name] {
				options = append(options, arg)
				if !hasInlineValue && i+1 < len(args) {
					i++
					options = append(options, args[i])
				}
				continue
			}
		}
		positionals = append(positionals, arg)
	}
	return append(options, positionals...)
}

func runShare(args []string) {
	subcommand, subArgs := normalizeShareArgs(args)
	switch subcommand {
	case "auto":
		runShareAuto(subArgs)
	case "list":
		runShareList(subArgs)
	case "new":
		runShareNew(subArgs)
	case "use":
		runShareUse(subArgs)
	case "next":
		runShareNext(subArgs)
	case "status":
		runShareStatus(subArgs)
	case "release":
		runShareRelease(subArgs)
	case "help", "--help", "-h":
		printShareUsage()
	default:
		fmt.Fprintf(os.Stderr, "Unknown share subcommand: %s\n\n", subcommand)
		printShareUsage()
		os.Exit(1)
	}
}

func printShareUsage() {
	fmt.Println(`Usage: cc-connect share [command|slot|title] [options]

Commands:
  <none>    Resume the current local shared slot, or create a new one if none is bound
  list      List shared slots for a workspace
  new       Start a new interactive Codex session and bind it to a fresh slot
  use       Resume an existing shared slot locally
  next      Switch the current local shared slot to another account automatically
  status    Show one slot's registry + lease state
  release   Release a slot lease (typically with --force)

Examples:
  cc-connect share
  cc-connect share --account acc2
  cc-connect share "train debug"
  cc-connect share s003
  cc-connect share next
  cc-connect share list --project harness
  cc-connect share new --project harness --account acc2 --title "train debug"
  cc-connect share use s003 --project harness --account acc1
  cc-connect share status s003 --project harness
  cc-connect share release s003 --project harness --force`)
}

func resolveWorkspace(flagValue string) (string, error) {
	workspace := strings.TrimSpace(flagValue)
	if workspace == "" {
		var err error
		workspace, err = os.Getwd()
		if err != nil {
			return "", err
		}
	}
	abs, err := filepath.Abs(workspace)
	if err != nil {
		return "", err
	}
	return filepath.Clean(abs), nil
}

func configuredWorkDir(proj config.ProjectConfig) string {
	workDir, _ := proj.Agent.Options["work_dir"].(string)
	workDir = strings.TrimSpace(workDir)
	if workDir == "" {
		return ""
	}
	abs, err := filepath.Abs(workDir)
	if err != nil {
		return workDir
	}
	return filepath.Clean(abs)
}

func selectShareProject(cfg *config.Config, projectName, workspace string) (*config.ProjectConfig, error) {
	if projectName != "" {
		for i := range cfg.Projects {
			if cfg.Projects[i].Name == projectName {
				return &cfg.Projects[i], nil
			}
		}
		return nil, fmt.Errorf("project %q not found", projectName)
	}

	var workspaceMatches []*config.ProjectConfig
	for i := range cfg.Projects {
		if configuredWorkDir(cfg.Projects[i]) == workspace {
			workspaceMatches = append(workspaceMatches, &cfg.Projects[i])
		}
	}
	if len(workspaceMatches) == 1 {
		return workspaceMatches[0], nil
	}

	if len(cfg.Projects) == 1 {
		return &cfg.Projects[0], nil
	}

	return nil, fmt.Errorf("multiple projects configured; pass --project")
}

func cloneAgentOptions(src map[string]any) map[string]any {
	out := make(map[string]any, len(src)+1)
	for k, v := range src {
		out[k] = v
	}
	return out
}

func activeProviderName(proj config.ProjectConfig) string {
	name, _ := proj.Agent.Options["provider"].(string)
	return strings.TrimSpace(name)
}

func loadShareRuntime(configFlag, projectName, workspace, account string) (*shareProjectRuntime, error) {
	configPath := resolveConfigPath(configFlag)
	cfg, err := config.Load(configPath)
	if err != nil {
		return nil, err
	}

	proj, err := selectShareProject(cfg, projectName, workspace)
	if err != nil {
		return nil, err
	}
	if proj.Agent.Type != "codex" {
		return nil, fmt.Errorf("share only supports codex projects, got %q", proj.Agent.Type)
	}

	opts := cloneAgentOptions(proj.Agent.Options)
	opts["work_dir"] = workspace

	agent, err := core.CreateAgent(proj.Agent.Type, opts)
	if err != nil {
		return nil, err
	}

	if ps, ok := agent.(core.ProviderSwitcher); ok && len(proj.Agent.Providers) > 0 {
		providers := make([]core.ProviderConfig, len(proj.Agent.Providers))
		for i, p := range proj.Agent.Providers {
			providers[i] = core.ProviderConfig{
				Name:         p.Name,
				APIKey:       p.APIKey,
				BaseURL:      p.BaseURL,
				Model:        p.Model,
				Models:       convertProviderModels(p.Models),
				Thinking:     p.Thinking,
				Env:          p.Env,
				Priority:     p.Priority,
				CooldownSec:  p.CooldownSec,
				AutoFailover: p.AutoFailover,
			}
		}
		ps.SetProviders(providers)

		targetProvider := strings.TrimSpace(account)
		if targetProvider == "" {
			targetProvider = activeProviderName(*proj)
		}
		if targetProvider != "" {
			if !ps.SetActiveProvider(targetProvider) {
				return nil, fmt.Errorf("provider/account %q not found in project %q", targetProvider, proj.Name)
			}
		}
	}

	model := ""
	if m, ok := agent.(interface{ GetModel() string }); ok {
		model = strings.TrimSpace(m.GetModel())
	}
	reasoning := ""
	if ra, ok := agent.(interface{ GetReasoningEffort() string }); ok {
		reasoning = strings.TrimSpace(ra.GetReasoningEffort())
	}
	mode := ""
	if ma, ok := agent.(interface{ GetMode() string }); ok {
		mode = strings.TrimSpace(ma.GetMode())
	}

	return &shareProjectRuntime{
		dataDir:         cfg.DataDir,
		projectName:     proj.Name,
		workspace:       workspace,
		agent:           agent,
		mode:            mode,
		model:           model,
		reasoningEffort: reasoning,
	}, nil
}

func (rt *shareProjectRuntime) sharedManager() *core.SharedSlotManager {
	return core.NewSharedSlotManager(core.SharedSessionStateDir(rt.dataDir))
}

func (rt *shareProjectRuntime) activeProvider() *core.ProviderConfig {
	switcher, ok := rt.agent.(core.ProviderSwitcher)
	if !ok {
		return nil
	}
	return switcher.GetActiveProvider()
}

func (rt *shareProjectRuntime) providers() []core.ProviderConfig {
	switcher, ok := rt.agent.(core.ProviderSwitcher)
	if !ok {
		return nil
	}
	return switcher.ListProviders()
}

func (rt *shareProjectRuntime) mergedEnv() []string {
	provider := rt.activeProvider()
	if provider == nil {
		return os.Environ()
	}
	var extra []string
	if provider.APIKey != "" {
		extra = append(extra, "OPENAI_API_KEY="+provider.APIKey)
	}
	if provider.BaseURL != "" {
		extra = append(extra, "OPENAI_BASE_URL="+provider.BaseURL)
	}
	keys := make([]string, 0, len(provider.Env))
	for key := range provider.Env {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	for _, key := range keys {
		extra = append(extra, key+"="+provider.Env[key])
	}
	return core.MergeEnv(os.Environ(), extra)
}

func (rt *shareProjectRuntime) syncSessionTranscript(sessionID string) error {
	sessionID = strings.TrimSpace(sessionID)
	if sessionID == "" {
		return nil
	}
	sess, err := rt.agent.StartSession(context.Background(), sessionID)
	if err != nil {
		return err
	}
	return sess.Close()
}

func (rt *shareProjectRuntime) listSessions(ctx context.Context) ([]core.AgentSessionInfo, error) {
	return rt.agent.ListSessions(ctx)
}

func (rt *shareProjectRuntime) codexArgs(sessionID string) []string {
	sessionID = strings.TrimSpace(sessionID)
	var args []string
	if sessionID != "" {
		args = append(args, "resume")
	}
	switch rt.mode {
	case "auto-edit", "full-auto":
		args = append(args, "--full-auto")
	case "yolo":
		args = append(args, "--dangerously-bypass-approvals-and-sandbox")
	}
	if rt.model != "" {
		args = append(args, "--model", rt.model)
	}
	if rt.reasoningEffort != "" {
		args = append(args, "-c", fmt.Sprintf("model_reasoning_effort=%q", rt.reasoningEffort))
	}
	args = append(args, "--cd", rt.workspace)
	if sessionID != "" {
		args = append(args, sessionID)
	}
	return args
}

func (m *localShareMonitor) refresh() {
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	sessions, err := m.runtime.listSessions(ctx)
	if err != nil {
		return
	}

	if m.sessionID != "" {
		for _, info := range sessions {
			if info.ID != m.sessionID {
				continue
			}
			if info.ModifiedAt.After(m.lastObserved) {
				m.lastObserved = info.ModifiedAt
				m.renew()
				m.syncRecord(m.sessionID)
			}
			return
		}
		return
	}

	var candidate *core.AgentSessionInfo
	for i := range sessions {
		info := sessions[i]
		if _, ok := m.before[info.ID]; ok {
			continue
		}
		if info.ModifiedAt.Before(m.startedAt.Add(-time.Minute)) {
			continue
		}
		if candidate == nil || info.ModifiedAt.After(candidate.ModifiedAt) {
			candidate = &info
		}
	}
	if candidate == nil {
		return
	}

	m.sessionID = candidate.ID
	m.lastObserved = candidate.ModifiedAt
	m.renew()
	m.syncRecord(candidate.ID)
}

func (m *localShareMonitor) syncRecord(sessionID string) {
	provider := m.runtime.activeProvider()
	update := core.SharedSlotRecordUpdate{
		SessionID: strings.TrimSpace(sessionID),
		UpdatedBy: "local",
	}
	if provider != nil {
		update.ProviderName = strings.TrimSpace(provider.Name)
		update.CodexHome = strings.TrimSpace(provider.Env["CODEX_HOME"])
	}
	_, _ = m.manager.UpdateSlot(m.workspace, m.slot, update)
}

func (m *localShareMonitor) renew() {
	_, _ = m.manager.AcquireLease(m.workspace, m.slot, core.SharedSlotLeaseRequest{
		HolderType: "local",
		HolderID:   m.holderID,
		HolderName: m.holderID,
		LeaseTTL:   core.DefaultSharedSlotLeaseTTL,
	})
}

func (m *localShareMonitor) run(ctx context.Context) {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	m.refresh()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			m.refresh()
		}
	}
}

func runInteractiveShare(rt *shareProjectRuntime, slotID, sessionID string) error {
	holderID := fmt.Sprintf("local:pid:%d", os.Getpid())
	manager := rt.sharedManager()
	if _, err := manager.AcquireLease(rt.workspace, slotID, core.SharedSlotLeaseRequest{
		HolderType: "local",
		HolderID:   holderID,
		HolderName: holderID,
		LeaseTTL:   core.DefaultSharedSlotLeaseTTL,
	}); err != nil {
		return err
	}
	defer manager.ReleaseLease(rt.workspace, slotID, "local", holderID, false)

	if preparer, ok := rt.agent.(interactiveSessionCatalogPreparer); ok {
		if err := preparer.PrepareInteractiveSessionCatalog(context.Background()); err != nil {
			return fmt.Errorf("prepare interactive session catalog: %w", err)
		}
	}

	if err := rt.syncSessionTranscript(sessionID); err != nil {
		return fmt.Errorf("sync session transcript: %w", err)
	}

	before := make(map[string]time.Time)
	if sessions, err := rt.listSessions(context.Background()); err == nil {
		for _, info := range sessions {
			before[info.ID] = info.ModifiedAt
		}
	}

	monitorCtx, cancelMonitor := context.WithCancel(context.Background())
	defer cancelMonitor()
	monitor := &localShareMonitor{
		runtime:   rt,
		manager:   manager,
		workspace: rt.workspace,
		slot:      slotID,
		holderID:  holderID,
		before:    before,
		sessionID: strings.TrimSpace(sessionID),
		startedAt: time.Now(),
	}
	if sessionID != "" {
		if mod, ok := before[sessionID]; ok {
			monitor.lastObserved = mod
		}
	}
	go monitor.run(monitorCtx)

	cmd := exec.Command("codex", rt.codexArgs(sessionID)...)
	cmd.Dir = rt.workspace
	cmd.Env = rt.mergedEnv()
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		cancelMonitor()
		monitor.refresh()
		if monitor.sessionID != "" {
			monitor.syncRecord(monitor.sessionID)
		}
		return err
	}

	cancelMonitor()
	monitor.refresh()
	if monitor.sessionID != "" {
		monitor.syncRecord(monitor.sessionID)
	}
	return nil
}

func shareProviderCooldownPath(dataDir string) string {
	return filepath.Join(core.SharedSessionStateDir(dataDir), "provider_cooldowns.json")
}

func loadShareProviderCooldowns(path string, now time.Time) (map[string]time.Time, error) {
	state := localProviderCooldownState{Providers: make(map[string]time.Time)}
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return state.Providers, nil
		}
		return nil, err
	}
	if err := json.Unmarshal(data, &state); err != nil {
		return nil, err
	}
	if state.Providers == nil {
		state.Providers = make(map[string]time.Time)
	}
	for name, until := range state.Providers {
		if !until.After(now) {
			delete(state.Providers, name)
		}
	}
	return state.Providers, nil
}

func saveShareProviderCooldowns(path string, cooldowns map[string]time.Time) error {
	state := localProviderCooldownState{Providers: cooldowns}
	if state.Providers == nil {
		state.Providers = make(map[string]time.Time)
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}
	return core.AtomicWriteFile(path, data, 0o644)
}

func shareProviderAutoFailoverEnabled(provider core.ProviderConfig) bool {
	if provider.AutoFailover == nil {
		return true
	}
	return *provider.AutoFailover
}

func shareProviderCooldownDuration(provider core.ProviderConfig) time.Duration {
	if provider.CooldownSec > 0 {
		return time.Duration(provider.CooldownSec) * time.Second
	}
	return 30 * time.Minute
}

func orderedShareProviders(providers []core.ProviderConfig, currentName string) []core.ProviderConfig {
	ordered := make([]core.ProviderConfig, len(providers))
	copy(ordered, providers)

	hasPriority := false
	for _, provider := range ordered {
		if provider.Priority != 0 {
			hasPriority = true
			break
		}
	}
	if hasPriority {
		sort.SliceStable(ordered, func(i, j int) bool {
			if ordered[i].Priority == ordered[j].Priority {
				return i < j
			}
			return ordered[i].Priority > ordered[j].Priority
		})
		return ordered
	}

	currentIdx := -1
	for idx, provider := range providers {
		if provider.Name == currentName {
			currentIdx = idx
			break
		}
	}
	if currentIdx == -1 || len(providers) <= 1 {
		return ordered
	}

	rotated := make([]core.ProviderConfig, 0, len(providers))
	for offset := 1; offset <= len(providers); offset++ {
		idx := (currentIdx + offset) % len(providers)
		rotated = append(rotated, providers[idx])
	}
	return rotated
}

func pickNextShareProvider(providers []core.ProviderConfig, currentName string, cooldowns map[string]time.Time, now time.Time) *core.ProviderConfig {
	passes := []bool{true, false}
	for _, respectCooldowns := range passes {
		for _, provider := range orderedShareProviders(providers, currentName) {
			name := strings.TrimSpace(provider.Name)
			if name == "" || name == currentName {
				continue
			}
			if !shareProviderAutoFailoverEnabled(provider) {
				continue
			}
			if respectCooldowns {
				if until, ok := cooldowns[name]; ok && until.After(now) {
					continue
				}
			}
			providerCopy := provider
			return &providerCopy
		}
	}
	return nil
}

func startNewLocalShare(rt *shareProjectRuntime, title string) error {
	slot, err := rt.sharedManager().CreateSlot(rt.workspace, title, "local")
	if err != nil {
		return err
	}
	if err := rt.sharedManager().SetLocalBinding(rt.workspace, slot.Slot); err != nil {
		return err
	}

	fmt.Fprintf(os.Stderr, "Starting slot %s in %s\n", slot.Slot, rt.workspace)
	return runInteractiveShare(rt, slot.Slot, "")
}

func resumeLocalShare(rt *shareProjectRuntime, slotID string) error {
	view, err := rt.sharedManager().GetSlot(rt.workspace, slotID)
	if err != nil {
		return err
	}
	if err := rt.sharedManager().SetLocalBinding(rt.workspace, slotID); err != nil {
		return err
	}

	fmt.Fprintf(os.Stderr, "Resuming slot %s in %s\n", slotID, rt.workspace)
	return runInteractiveShare(rt, slotID, view.Slot.SessionID)
}

func runShareAuto(args []string) {
	fs := flag.NewFlagSet("share", flag.ExitOnError)
	configFile := fs.String("config", "", "path to config file")
	project := fs.String("project", "", "project name")
	workspace := fs.String("workspace", "", "workspace path (default: current dir)")
	account := fs.String("account", "", "provider/account name")
	args = reorderShareFlagArgs(args, map[string]bool{
		"--config":    true,
		"--project":   true,
		"--workspace": true,
		"--account":   true,
	}, map[string]bool{
		"-h":     true,
		"--help": true,
	})
	_ = fs.Parse(args)

	resolvedWorkspace, err := resolveWorkspace(*workspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	rt, err := loadShareRuntime(*configFile, *project, resolvedWorkspace, *account)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	slotID, err := rt.sharedManager().GetLocalBinding(resolvedWorkspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if slotID != "" {
		if _, err := rt.sharedManager().GetSlot(resolvedWorkspace, slotID); err == nil {
			if err := resumeLocalShare(rt, slotID); err != nil {
				fmt.Fprintf(os.Stderr, "Error: %v\n", err)
				os.Exit(1)
			}
			return
		}
		_ = rt.sharedManager().ClearLocalBinding(resolvedWorkspace)
	}

	if err := startNewLocalShare(rt, ""); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runShareNext(args []string) {
	fs := flag.NewFlagSet("share next", flag.ExitOnError)
	configFile := fs.String("config", "", "path to config file")
	project := fs.String("project", "", "project name")
	workspace := fs.String("workspace", "", "workspace path (default: current dir)")
	args = reorderShareFlagArgs(args, map[string]bool{
		"--config":    true,
		"--project":   true,
		"--workspace": true,
	}, map[string]bool{
		"-h":     true,
		"--help": true,
	})
	_ = fs.Parse(args)

	resolvedWorkspace, err := resolveWorkspace(*workspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	rt, err := loadShareRuntime(*configFile, *project, resolvedWorkspace, "")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	switcher, ok := rt.agent.(core.ProviderSwitcher)
	if !ok {
		fmt.Fprintln(os.Stderr, "Error: current agent does not support provider switching")
		os.Exit(1)
	}

	manager := rt.sharedManager()
	slotID, err := manager.GetLocalBinding(resolvedWorkspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	currentProvider := ""
	if slotID != "" {
		if view, err := manager.GetSlot(resolvedWorkspace, slotID); err == nil {
			currentProvider = strings.TrimSpace(view.Slot.ProviderName)
		} else {
			_ = manager.ClearLocalBinding(resolvedWorkspace)
			slotID = ""
		}
	}
	if currentProvider == "" {
		if active := rt.activeProvider(); active != nil {
			currentProvider = strings.TrimSpace(active.Name)
		}
	}

	now := time.Now()
	cooldownPath := shareProviderCooldownPath(rt.dataDir)
	cooldowns, err := loadShareProviderCooldowns(cooldownPath, now)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if currentProvider != "" {
		for _, provider := range rt.providers() {
			if provider.Name == currentProvider {
				cooldowns[currentProvider] = now.Add(shareProviderCooldownDuration(provider))
				break
			}
		}
	}

	nextProvider := pickNextShareProvider(rt.providers(), currentProvider, cooldowns, now)
	if nextProvider == nil {
		fmt.Fprintln(os.Stderr, "Error: no alternate provider/account is currently available")
		os.Exit(1)
	}
	if err := saveShareProviderCooldowns(cooldownPath, cooldowns); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if !switcher.SetActiveProvider(nextProvider.Name) {
		fmt.Fprintf(os.Stderr, "Error: provider/account %q not found\n", nextProvider.Name)
		os.Exit(1)
	}

	if currentProvider != "" {
		fmt.Fprintf(os.Stderr, "Switching account: %s -> %s\n", currentProvider, nextProvider.Name)
	} else {
		fmt.Fprintf(os.Stderr, "Switching account to %s\n", nextProvider.Name)
	}

	if slotID != "" {
		if err := resumeLocalShare(rt, slotID); err != nil {
			fmt.Fprintf(os.Stderr, "Error: %v\n", err)
			os.Exit(1)
		}
		return
	}
	if err := startNewLocalShare(rt, ""); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runShareList(args []string) {
	fs := flag.NewFlagSet("share list", flag.ExitOnError)
	configFile := fs.String("config", "", "path to config file")
	project := fs.String("project", "", "project name")
	workspace := fs.String("workspace", "", "workspace path (default: current dir)")
	args = reorderShareFlagArgs(args, map[string]bool{
		"--config":    true,
		"--project":   true,
		"--workspace": true,
	}, map[string]bool{
		"-h":     true,
		"--help": true,
	})
	_ = fs.Parse(args)

	resolvedWorkspace, err := resolveWorkspace(*workspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	rt, err := loadShareRuntime(*configFile, *project, resolvedWorkspace, "")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	views, err := rt.sharedManager().ListSlots(resolvedWorkspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if len(views) == 0 {
		fmt.Println("No shared slots for this workspace.")
		return
	}
	for _, view := range views {
		fmt.Println(formatShareCLIView(view))
	}
}

func runShareNew(args []string) {
	fs := flag.NewFlagSet("share new", flag.ExitOnError)
	configFile := fs.String("config", "", "path to config file")
	project := fs.String("project", "", "project name")
	workspace := fs.String("workspace", "", "workspace path (default: current dir)")
	account := fs.String("account", "", "provider/account name")
	title := fs.String("title", "", "slot title")
	args = reorderShareFlagArgs(args, map[string]bool{
		"--config":    true,
		"--project":   true,
		"--workspace": true,
		"--account":   true,
		"--title":     true,
	}, map[string]bool{
		"-h":     true,
		"--help": true,
	})
	_ = fs.Parse(args)

	resolvedWorkspace, err := resolveWorkspace(*workspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	rt, err := loadShareRuntime(*configFile, *project, resolvedWorkspace, *account)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	if strings.TrimSpace(*title) == "" && fs.NArg() > 0 {
		*title = strings.TrimSpace(strings.Join(fs.Args(), " "))
	}
	if err := startNewLocalShare(rt, *title); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runShareUse(args []string) {
	fs := flag.NewFlagSet("share use", flag.ExitOnError)
	configFile := fs.String("config", "", "path to config file")
	project := fs.String("project", "", "project name")
	workspace := fs.String("workspace", "", "workspace path (default: current dir)")
	account := fs.String("account", "", "provider/account name")
	args = reorderShareFlagArgs(args, map[string]bool{
		"--config":    true,
		"--project":   true,
		"--workspace": true,
		"--account":   true,
	}, map[string]bool{
		"-h":     true,
		"--help": true,
	})
	_ = fs.Parse(args)

	if fs.NArg() < 1 {
		fmt.Fprintln(os.Stderr, "Error: slot is required")
		fs.Usage()
		os.Exit(1)
	}
	slotID := strings.TrimSpace(fs.Arg(0))

	resolvedWorkspace, err := resolveWorkspace(*workspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	rt, err := loadShareRuntime(*configFile, *project, resolvedWorkspace, *account)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	if err := resumeLocalShare(rt, slotID); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runShareStatus(args []string) {
	fs := flag.NewFlagSet("share status", flag.ExitOnError)
	configFile := fs.String("config", "", "path to config file")
	project := fs.String("project", "", "project name")
	workspace := fs.String("workspace", "", "workspace path (default: current dir)")
	args = reorderShareFlagArgs(args, map[string]bool{
		"--config":    true,
		"--project":   true,
		"--workspace": true,
	}, map[string]bool{
		"-h":     true,
		"--help": true,
	})
	_ = fs.Parse(args)

	if fs.NArg() < 1 {
		fmt.Fprintln(os.Stderr, "Error: slot is required")
		fs.Usage()
		os.Exit(1)
	}
	slotID := strings.TrimSpace(fs.Arg(0))

	resolvedWorkspace, err := resolveWorkspace(*workspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	rt, err := loadShareRuntime(*configFile, *project, resolvedWorkspace, "")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	view, err := rt.sharedManager().GetSlot(resolvedWorkspace, slotID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Slot: %s\n", view.Slot.Slot)
	if view.Slot.Title != "" {
		fmt.Printf("Title: %s\n", view.Slot.Title)
	}
	if view.Slot.SessionID != "" {
		fmt.Printf("Session: %s\n", view.Slot.SessionID)
	}
	if view.Slot.ProviderName != "" {
		fmt.Printf("Provider: %s\n", view.Slot.ProviderName)
	}
	fmt.Printf("Lease: %s\n", formatShareCLILease(view.Lease, time.Now()))
}

func runShareRelease(args []string) {
	fs := flag.NewFlagSet("share release", flag.ExitOnError)
	configFile := fs.String("config", "", "path to config file")
	project := fs.String("project", "", "project name")
	workspace := fs.String("workspace", "", "workspace path (default: current dir)")
	force := fs.Bool("force", false, "force release even if held by another client")
	args = reorderShareFlagArgs(args, map[string]bool{
		"--config":    true,
		"--project":   true,
		"--workspace": true,
	}, map[string]bool{
		"--force": true,
		"-h":      true,
		"--help":  true,
	})
	_ = fs.Parse(args)

	if fs.NArg() < 1 {
		fmt.Fprintln(os.Stderr, "Error: slot is required")
		fs.Usage()
		os.Exit(1)
	}
	slotID := strings.TrimSpace(fs.Arg(0))

	resolvedWorkspace, err := resolveWorkspace(*workspace)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	rt, err := loadShareRuntime(*configFile, *project, resolvedWorkspace, "")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}

	holderID := fmt.Sprintf("local:pid:%d", os.Getpid())
	if err := rt.sharedManager().ReleaseLease(resolvedWorkspace, slotID, "local", holderID, *force); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("Released slot %s\n", slotID)
}
