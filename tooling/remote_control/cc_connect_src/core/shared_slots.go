package core

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"syscall"
	"time"
)

const (
	sharedSlotStateVersion    = 1
	DefaultSharedSlotLeaseTTL = time.Hour
)

var (
	ErrSharedSlotNotFound = errors.New("shared slot not found")
	ErrSharedSlotBusy     = errors.New("shared slot is busy")
)

// SharedSessionStateDir returns the state directory used for shared slot
// registry and lease persistence.
func SharedSessionStateDir(dataDir string) string {
	if override := strings.TrimSpace(os.Getenv("CC_SHARED_SESSION_DIR")); override != "" {
		return override
	}
	dataDir = strings.TrimSpace(dataDir)
	if dataDir != "" {
		return filepath.Join(dataDir, "shared_slots")
	}
	if home, err := os.UserHomeDir(); err == nil {
		return filepath.Join(home, ".cc-connect", "shared_slots")
	}
	return filepath.Join(".cc-connect", "shared_slots")
}

// SharedSessionStateDirFromStore derives the shared state directory from a
// session store file path.
func SharedSessionStateDirFromStore(storePath string) string {
	storePath = strings.TrimSpace(storePath)
	if storePath == "" {
		return SharedSessionStateDir("")
	}
	storeDir := filepath.Dir(storePath)
	if filepath.Base(storeDir) == "sessions" {
		return SharedSessionStateDir(filepath.Dir(storeDir))
	}
	return SharedSessionStateDir(storeDir)
}

// SharedSlotRecord stores one workspace slot binding to a backend session.
type SharedSlotRecord struct {
	Slot         string    `json:"slot"`
	SessionID    string    `json:"session_id,omitempty"`
	Title        string    `json:"title,omitempty"`
	ProviderName string    `json:"provider_name,omitempty"`
	CodexHome    string    `json:"codex_home,omitempty"`
	CreatedAt    time.Time `json:"created_at"`
	UpdatedAt    time.Time `json:"updated_at"`
	UpdatedBy    string    `json:"updated_by,omitempty"`
	Archived     bool      `json:"archived,omitempty"`
}

// SharedSlotLease represents the current holder of a workspace slot.
type SharedSlotLease struct {
	Workspace  string    `json:"workspace"`
	Slot       string    `json:"slot"`
	HolderType string    `json:"holder_type"`
	HolderID   string    `json:"holder_id"`
	HolderName string    `json:"holder_name,omitempty"`
	AcquiredAt time.Time `json:"acquired_at"`
	UpdatedAt  time.Time `json:"updated_at"`
	LeaseUntil time.Time `json:"lease_until"`
}

// SharedSlotView is the combined registry and lease view returned to callers.
type SharedSlotView struct {
	Slot  SharedSlotRecord `json:"slot"`
	Lease *SharedSlotLease `json:"lease,omitempty"`
}

// SharedSlotBusyError exposes the active lease when a slot cannot be acquired.
type SharedSlotBusyError struct {
	Lease SharedSlotLease
}

func (e *SharedSlotBusyError) Error() string {
	holder := strings.TrimSpace(e.Lease.HolderName)
	if holder == "" {
		holder = strings.TrimSpace(e.Lease.HolderID)
	}
	if holder == "" {
		holder = e.Lease.HolderType
	}
	return fmt.Sprintf("%s: slot %s held by %s until %s",
		ErrSharedSlotBusy.Error(),
		e.Lease.Slot,
		holder,
		e.Lease.LeaseUntil.Format(time.RFC3339),
	)
}

// SharedSlotLeaseRequest describes the desired slot acquisition or renewal.
type SharedSlotLeaseRequest struct {
	HolderType string
	HolderID   string
	HolderName string
	LeaseTTL   time.Duration
	Force      bool
}

// SharedSlotRecordUpdate patches registry metadata. Empty strings are ignored.
type SharedSlotRecordUpdate struct {
	SessionID    string
	Title        string
	ProviderName string
	CodexHome    string
	UpdatedBy    string
	Archived     *bool
}

type sharedSlotRegistry struct {
	Version       int                              `json:"version"`
	Workspaces    map[string]*sharedWorkspaceSlots `json:"workspaces"`
	LocalBindings map[string]string                `json:"local_bindings,omitempty"`
}

type sharedWorkspaceSlots struct {
	Slots map[string]*SharedSlotRecord `json:"slots"`
}

type sharedSlotLeaseState struct {
	Version int                         `json:"version"`
	Leases  map[string]*SharedSlotLease `json:"leases"`
}

type sharedSlotState struct {
	Registry sharedSlotRegistry
	Leases   sharedSlotLeaseState
}

// SharedSlotManager owns persistent slot registry and lease state.
type SharedSlotManager struct {
	rootDir string
	now     func() time.Time
}

func NewSharedSlotManager(rootDir string) *SharedSlotManager {
	return &SharedSlotManager{
		rootDir: strings.TrimSpace(rootDir),
		now:     time.Now,
	}
}

func (m *SharedSlotManager) registryPath() string {
	return filepath.Join(m.stateDir(), "registry.json")
}

func (m *SharedSlotManager) leasesPath() string {
	return filepath.Join(m.stateDir(), "leases.json")
}

func (m *SharedSlotManager) lockPath() string {
	return filepath.Join(m.stateDir(), ".lock")
}

func (m *SharedSlotManager) stateDir() string {
	if strings.TrimSpace(m.rootDir) != "" {
		return m.rootDir
	}
	return SharedSessionStateDir("")
}

func normalizeSharedWorkspace(workspace string) string {
	workspace = strings.TrimSpace(workspace)
	if workspace == "" {
		return ""
	}
	if abs, err := filepath.Abs(workspace); err == nil {
		workspace = abs
	}
	return filepath.Clean(workspace)
}

func sharedSlotLeaseKey(workspace, slot string) string {
	return normalizeSharedWorkspace(workspace) + "\x00" + strings.TrimSpace(slot)
}

func slotNumber(slot string) int {
	slot = strings.TrimSpace(strings.TrimPrefix(strings.ToLower(slot), "s"))
	n, err := strconv.Atoi(slot)
	if err != nil {
		return -1
	}
	return n
}

func nextSharedSlotID(slots map[string]*SharedSlotRecord) string {
	maxID := 0
	for slot := range slots {
		if n := slotNumber(slot); n > maxID {
			maxID = n
		}
	}
	return fmt.Sprintf("s%03d", maxID+1)
}

func copySharedSlotRecord(src *SharedSlotRecord) SharedSlotRecord {
	if src == nil {
		return SharedSlotRecord{}
	}
	return *src
}

func copySharedSlotLease(src *SharedSlotLease) *SharedSlotLease {
	if src == nil {
		return nil
	}
	cp := *src
	return &cp
}

func parseLocalLeasePID(holderID string) (int, bool) {
	holderID = strings.TrimSpace(holderID)
	const prefix = "local:pid:"
	if !strings.HasPrefix(holderID, prefix) {
		return 0, false
	}
	pid, err := strconv.Atoi(strings.TrimSpace(strings.TrimPrefix(holderID, prefix)))
	if err != nil || pid <= 0 {
		return 0, false
	}
	return pid, true
}

func localLeaseHolderAlive(lease *SharedSlotLease) bool {
	if lease == nil || strings.TrimSpace(lease.HolderType) != "local" {
		return true
	}
	pid, ok := parseLocalLeasePID(lease.HolderID)
	if !ok {
		return true
	}
	err := syscall.Kill(pid, 0)
	return err == nil || errors.Is(err, syscall.EPERM)
}

func normalizeSharedSlotState(state *sharedSlotState, now time.Time) bool {
	dirty := false
	if state.Registry.Version == 0 {
		state.Registry.Version = sharedSlotStateVersion
		dirty = true
	}
	if state.Registry.Workspaces == nil {
		state.Registry.Workspaces = make(map[string]*sharedWorkspaceSlots)
		dirty = true
	}
	if state.Registry.LocalBindings == nil {
		state.Registry.LocalBindings = make(map[string]string)
		dirty = true
	}
	for _, ws := range state.Registry.Workspaces {
		if ws == nil {
			continue
		}
		if ws.Slots == nil {
			ws.Slots = make(map[string]*SharedSlotRecord)
			dirty = true
		}
	}
	if state.Leases.Version == 0 {
		state.Leases.Version = sharedSlotStateVersion
		dirty = true
	}
	if state.Leases.Leases == nil {
		state.Leases.Leases = make(map[string]*SharedSlotLease)
		dirty = true
	}
	for key, lease := range state.Leases.Leases {
		if lease == nil || !lease.LeaseUntil.After(now) || !localLeaseHolderAlive(lease) {
			delete(state.Leases.Leases, key)
			dirty = true
		}
	}
	return dirty
}

func (m *SharedSlotManager) loadState() (*sharedSlotState, error) {
	state := &sharedSlotState{
		Registry: sharedSlotRegistry{
			Version:       sharedSlotStateVersion,
			Workspaces:    make(map[string]*sharedWorkspaceSlots),
			LocalBindings: make(map[string]string),
		},
		Leases: sharedSlotLeaseState{
			Version: sharedSlotStateVersion,
			Leases:  make(map[string]*SharedSlotLease),
		},
	}

	if data, err := os.ReadFile(m.registryPath()); err == nil {
		if err := json.Unmarshal(data, &state.Registry); err != nil {
			return nil, fmt.Errorf("parse shared slot registry: %w", err)
		}
	} else if !os.IsNotExist(err) {
		return nil, fmt.Errorf("read shared slot registry: %w", err)
	}

	if data, err := os.ReadFile(m.leasesPath()); err == nil {
		if err := json.Unmarshal(data, &state.Leases); err != nil {
			return nil, fmt.Errorf("parse shared slot leases: %w", err)
		}
	} else if !os.IsNotExist(err) {
		return nil, fmt.Errorf("read shared slot leases: %w", err)
	}

	normalizeSharedSlotState(state, m.now())
	return state, nil
}

func (m *SharedSlotManager) saveState(state *sharedSlotState) error {
	if err := os.MkdirAll(m.stateDir(), 0o755); err != nil {
		return err
	}

	registryData, err := json.MarshalIndent(state.Registry, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal shared slot registry: %w", err)
	}
	if err := AtomicWriteFile(m.registryPath(), registryData, 0o644); err != nil {
		return fmt.Errorf("write shared slot registry: %w", err)
	}

	leaseData, err := json.MarshalIndent(state.Leases, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal shared slot leases: %w", err)
	}
	if err := AtomicWriteFile(m.leasesPath(), leaseData, 0o644); err != nil {
		return fmt.Errorf("write shared slot leases: %w", err)
	}

	return nil
}

func (m *SharedSlotManager) withLockedState(fn func(*sharedSlotState) (bool, error)) error {
	if err := os.MkdirAll(m.stateDir(), 0o755); err != nil {
		return err
	}

	lockFile, err := os.OpenFile(m.lockPath(), os.O_CREATE|os.O_RDWR, 0o644)
	if err != nil {
		return fmt.Errorf("open shared slot lock: %w", err)
	}
	defer lockFile.Close()

	if err := syscall.Flock(int(lockFile.Fd()), syscall.LOCK_EX); err != nil {
		return fmt.Errorf("lock shared slot state: %w", err)
	}
	defer syscall.Flock(int(lockFile.Fd()), syscall.LOCK_UN)

	state, err := m.loadState()
	if err != nil {
		return err
	}
	dirty := normalizeSharedSlotState(state, m.now())

	changed, err := fn(state)
	if err != nil {
		return err
	}
	if !dirty && !changed {
		return nil
	}
	return m.saveState(state)
}

func (m *SharedSlotManager) ensureWorkspaceState(state *sharedSlotState, workspace string) *sharedWorkspaceSlots {
	ws := state.Registry.Workspaces[workspace]
	if ws == nil {
		ws = &sharedWorkspaceSlots{Slots: make(map[string]*SharedSlotRecord)}
		state.Registry.Workspaces[workspace] = ws
	} else if ws.Slots == nil {
		ws.Slots = make(map[string]*SharedSlotRecord)
	}
	return ws
}

// GetLocalBinding returns the locally preferred slot for a workspace.
func (m *SharedSlotManager) GetLocalBinding(workspace string) (string, error) {
	workspace = normalizeSharedWorkspace(workspace)
	if workspace == "" {
		return "", fmt.Errorf("workspace is required")
	}

	var slot string
	err := m.withLockedState(func(state *sharedSlotState) (bool, error) {
		slot = strings.TrimSpace(state.Registry.LocalBindings[workspace])
		return false, nil
	})
	if err != nil {
		return "", err
	}
	return slot, nil
}

// SetLocalBinding updates the locally preferred slot for a workspace.
func (m *SharedSlotManager) SetLocalBinding(workspace, slot string) error {
	workspace = normalizeSharedWorkspace(workspace)
	slot = strings.TrimSpace(slot)
	if workspace == "" || slot == "" {
		return fmt.Errorf("workspace and slot are required")
	}

	return m.withLockedState(func(state *sharedSlotState) (bool, error) {
		ws := state.Registry.Workspaces[workspace]
		if ws == nil || ws.Slots[slot] == nil {
			return false, ErrSharedSlotNotFound
		}
		if strings.TrimSpace(state.Registry.LocalBindings[workspace]) == slot {
			return false, nil
		}
		state.Registry.LocalBindings[workspace] = slot
		return true, nil
	})
}

// ClearLocalBinding removes any locally preferred slot for a workspace.
func (m *SharedSlotManager) ClearLocalBinding(workspace string) error {
	workspace = normalizeSharedWorkspace(workspace)
	if workspace == "" {
		return fmt.Errorf("workspace is required")
	}

	return m.withLockedState(func(state *sharedSlotState) (bool, error) {
		if _, ok := state.Registry.LocalBindings[workspace]; !ok {
			return false, nil
		}
		delete(state.Registry.LocalBindings, workspace)
		return true, nil
	})
}

// CreateSlot allocates a new slot for a workspace.
func (m *SharedSlotManager) CreateSlot(workspace, title, updatedBy string) (*SharedSlotRecord, error) {
	workspace = normalizeSharedWorkspace(workspace)
	if workspace == "" {
		return nil, fmt.Errorf("workspace is required")
	}

	var created SharedSlotRecord
	err := m.withLockedState(func(state *sharedSlotState) (bool, error) {
		ws := m.ensureWorkspaceState(state, workspace)
		slotID := nextSharedSlotID(ws.Slots)
		now := m.now()
		record := &SharedSlotRecord{
			Slot:      slotID,
			Title:     strings.TrimSpace(title),
			CreatedAt: now,
			UpdatedAt: now,
			UpdatedBy: strings.TrimSpace(updatedBy),
		}
		ws.Slots[slotID] = record
		created = copySharedSlotRecord(record)
		return true, nil
	})
	if err != nil {
		return nil, err
	}
	return &created, nil
}

// ListSlots lists all slots for the workspace with active lease info.
func (m *SharedSlotManager) ListSlots(workspace string) ([]SharedSlotView, error) {
	workspace = normalizeSharedWorkspace(workspace)
	if workspace == "" {
		return nil, fmt.Errorf("workspace is required")
	}

	var views []SharedSlotView
	err := m.withLockedState(func(state *sharedSlotState) (bool, error) {
		ws := state.Registry.Workspaces[workspace]
		if ws == nil || len(ws.Slots) == 0 {
			views = nil
			return false, nil
		}
		views = make([]SharedSlotView, 0, len(ws.Slots))
		for slotID, record := range ws.Slots {
			views = append(views, SharedSlotView{
				Slot:  copySharedSlotRecord(record),
				Lease: copySharedSlotLease(state.Leases.Leases[sharedSlotLeaseKey(workspace, slotID)]),
			})
		}
		sort.Slice(views, func(i, j int) bool {
			left := slotNumber(views[i].Slot.Slot)
			right := slotNumber(views[j].Slot.Slot)
			if left == right {
				return views[i].Slot.Slot < views[j].Slot.Slot
			}
			return left < right
		})
		return false, nil
	})
	if err != nil {
		return nil, err
	}
	return views, nil
}

// GetSlot returns a single slot view for the workspace.
func (m *SharedSlotManager) GetSlot(workspace, slot string) (*SharedSlotView, error) {
	workspace = normalizeSharedWorkspace(workspace)
	slot = strings.TrimSpace(slot)
	if workspace == "" || slot == "" {
		return nil, fmt.Errorf("workspace and slot are required")
	}

	var view *SharedSlotView
	err := m.withLockedState(func(state *sharedSlotState) (bool, error) {
		ws := state.Registry.Workspaces[workspace]
		if ws == nil {
			return false, ErrSharedSlotNotFound
		}
		record := ws.Slots[slot]
		if record == nil {
			return false, ErrSharedSlotNotFound
		}
		view = &SharedSlotView{
			Slot:  copySharedSlotRecord(record),
			Lease: copySharedSlotLease(state.Leases.Leases[sharedSlotLeaseKey(workspace, slot)]),
		}
		return false, nil
	})
	if err != nil {
		return nil, err
	}
	return view, nil
}

// UpdateSlot patches persisted slot metadata.
func (m *SharedSlotManager) UpdateSlot(workspace, slot string, update SharedSlotRecordUpdate) (*SharedSlotRecord, error) {
	workspace = normalizeSharedWorkspace(workspace)
	slot = strings.TrimSpace(slot)
	if workspace == "" || slot == "" {
		return nil, fmt.Errorf("workspace and slot are required")
	}

	var updated SharedSlotRecord
	err := m.withLockedState(func(state *sharedSlotState) (bool, error) {
		ws := state.Registry.Workspaces[workspace]
		if ws == nil {
			return false, ErrSharedSlotNotFound
		}
		record := ws.Slots[slot]
		if record == nil {
			return false, ErrSharedSlotNotFound
		}

		changed := false
		if value := strings.TrimSpace(update.SessionID); value != "" && value != record.SessionID {
			record.SessionID = value
			changed = true
		}
		if value := strings.TrimSpace(update.Title); value != "" && value != record.Title {
			record.Title = value
			changed = true
		}
		if value := strings.TrimSpace(update.ProviderName); value != "" && value != record.ProviderName {
			record.ProviderName = value
			changed = true
		}
		if value := strings.TrimSpace(update.CodexHome); value != "" && value != record.CodexHome {
			record.CodexHome = value
			changed = true
		}
		if update.Archived != nil && record.Archived != *update.Archived {
			record.Archived = *update.Archived
			changed = true
		}
		if value := strings.TrimSpace(update.UpdatedBy); value != "" && value != record.UpdatedBy {
			record.UpdatedBy = value
			changed = true
		}
		if changed {
			record.UpdatedAt = m.now()
		}
		updated = copySharedSlotRecord(record)
		return changed, nil
	})
	if err != nil {
		return nil, err
	}
	return &updated, nil
}

// AcquireLease acquires or renews a slot lease.
func (m *SharedSlotManager) AcquireLease(workspace, slot string, req SharedSlotLeaseRequest) (*SharedSlotLease, error) {
	workspace = normalizeSharedWorkspace(workspace)
	slot = strings.TrimSpace(slot)
	req.HolderType = strings.TrimSpace(req.HolderType)
	req.HolderID = strings.TrimSpace(req.HolderID)
	req.HolderName = strings.TrimSpace(req.HolderName)
	if workspace == "" || slot == "" || req.HolderType == "" || req.HolderID == "" {
		return nil, fmt.Errorf("workspace, slot, holder_type and holder_id are required")
	}
	if req.LeaseTTL <= 0 {
		req.LeaseTTL = DefaultSharedSlotLeaseTTL
	}

	var leaseCopy *SharedSlotLease
	err := m.withLockedState(func(state *sharedSlotState) (bool, error) {
		ws := state.Registry.Workspaces[workspace]
		if ws == nil || ws.Slots[slot] == nil {
			return false, ErrSharedSlotNotFound
		}

		key := sharedSlotLeaseKey(workspace, slot)
		now := m.now()
		current := state.Leases.Leases[key]
		if current != nil && current.LeaseUntil.After(now) {
			sameHolder := current.HolderType == req.HolderType && current.HolderID == req.HolderID
			if !sameHolder && !req.Force {
				return false, &SharedSlotBusyError{Lease: *copySharedSlotLease(current)}
			}
			current.HolderType = req.HolderType
			current.HolderID = req.HolderID
			current.HolderName = req.HolderName
			if current.AcquiredAt.IsZero() || sameHolder {
				// keep the original acquired time on renewals by the same holder
			} else {
				current.AcquiredAt = now
			}
			current.UpdatedAt = now
			current.LeaseUntil = now.Add(req.LeaseTTL)
			leaseCopy = copySharedSlotLease(current)
			return true, nil
		}

		lease := &SharedSlotLease{
			Workspace:  workspace,
			Slot:       slot,
			HolderType: req.HolderType,
			HolderID:   req.HolderID,
			HolderName: req.HolderName,
			AcquiredAt: now,
			UpdatedAt:  now,
			LeaseUntil: now.Add(req.LeaseTTL),
		}
		state.Leases.Leases[key] = lease
		leaseCopy = copySharedSlotLease(lease)
		return true, nil
	})
	if err != nil {
		return nil, err
	}
	return leaseCopy, nil
}

// ReleaseLease releases the current slot lease if it belongs to the holder or
// force is true.
func (m *SharedSlotManager) ReleaseLease(workspace, slot, holderType, holderID string, force bool) error {
	workspace = normalizeSharedWorkspace(workspace)
	slot = strings.TrimSpace(slot)
	holderType = strings.TrimSpace(holderType)
	holderID = strings.TrimSpace(holderID)
	if workspace == "" || slot == "" {
		return fmt.Errorf("workspace and slot are required")
	}

	return m.withLockedState(func(state *sharedSlotState) (bool, error) {
		key := sharedSlotLeaseKey(workspace, slot)
		current := state.Leases.Leases[key]
		if current == nil {
			return false, nil
		}
		sameHolder := current.HolderType == holderType && current.HolderID == holderID
		if !sameHolder && !force {
			return false, &SharedSlotBusyError{Lease: *copySharedSlotLease(current)}
		}
		delete(state.Leases.Leases, key)
		return true, nil
	})
}
