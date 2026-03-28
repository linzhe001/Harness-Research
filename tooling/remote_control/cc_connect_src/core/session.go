package core

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"sync"
	"time"
)

// Session tracks one conversation between a user and the agent.
type Session struct {
	ID                    string            `json:"id"`
	Name                  string            `json:"name"`
	AgentSessionID        string            `json:"agent_session_id"`
	AgentSessionScope     string            `json:"agent_session_scope,omitempty"`
	ScopedAgentSessionIDs map[string]string `json:"scoped_agent_session_ids,omitempty"`
	AgentType             string            `json:"agent_type,omitempty"`
	History               []HistoryEntry    `json:"history"`
	CreatedAt             time.Time         `json:"created_at"`
	UpdatedAt             time.Time         `json:"updated_at"`

	mu   sync.Mutex `json:"-"`
	busy bool       `json:"-"`
}

func (s *Session) TryLock() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.busy {
		return false
	}
	s.busy = true
	return true
}

func (s *Session) Unlock() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.busy = false
	s.UpdatedAt = time.Now()
}

func (s *Session) AddHistory(role, content string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.History = append(s.History, HistoryEntry{
		Role:      role,
		Content:   content,
		Timestamp: time.Now(),
	})
}

func normalizeSessionScope(scope string) string {
	return strings.TrimSpace(scope)
}

func (s *Session) getExactScopedAgentSessionIDLocked(scope string) string {
	scope = normalizeSessionScope(scope)
	if scope == "" || s.ScopedAgentSessionIDs == nil {
		return ""
	}
	return strings.TrimSpace(s.ScopedAgentSessionIDs[scope])
}

func (s *Session) getScopedAgentSessionIDLocked(scope string) string {
	scope = normalizeSessionScope(scope)
	if scope != "" {
		if id := s.getExactScopedAgentSessionIDLocked(scope); id != "" {
			return id
		}
		if legacyScope := normalizeSessionScope(s.AgentSessionScope); legacyScope != "" && legacyScope == scope {
			return strings.TrimSpace(s.AgentSessionID)
		}
		return ""
	}

	if id := strings.TrimSpace(s.AgentSessionID); id != "" {
		return id
	}
	if activeScope := normalizeSessionScope(s.AgentSessionScope); activeScope != "" && s.ScopedAgentSessionIDs != nil {
		return strings.TrimSpace(s.ScopedAgentSessionIDs[activeScope])
	}
	return ""
}

func (s *Session) getResumeAgentSessionIDLocked(scope string) string {
	if id := s.getScopedAgentSessionIDLocked(scope); id != "" {
		return id
	}
	if id := strings.TrimSpace(s.AgentSessionID); id != "" {
		return id
	}

	activeScope := normalizeSessionScope(s.AgentSessionScope)
	if activeScope != "" {
		if id := s.getExactScopedAgentSessionIDLocked(activeScope); id != "" {
			return id
		}
	}

	if len(s.ScopedAgentSessionIDs) == 0 {
		return ""
	}

	scopes := make([]string, 0, len(s.ScopedAgentSessionIDs))
	for candidateScope, id := range s.ScopedAgentSessionIDs {
		if strings.TrimSpace(id) == "" {
			continue
		}
		scopes = append(scopes, candidateScope)
	}
	sort.Strings(scopes)
	for _, candidateScope := range scopes {
		if id := strings.TrimSpace(s.ScopedAgentSessionIDs[candidateScope]); id != "" {
			return id
		}
	}
	return ""
}

func (s *Session) setScopedAgentSessionIDLocked(scope, id, agentType string) {
	scope = normalizeSessionScope(scope)
	id = strings.TrimSpace(id)

	if scope != "" {
		if id == "" {
			if s.ScopedAgentSessionIDs != nil {
				delete(s.ScopedAgentSessionIDs, scope)
				if len(s.ScopedAgentSessionIDs) == 0 {
					s.ScopedAgentSessionIDs = nil
				}
			}
		} else {
			if s.ScopedAgentSessionIDs == nil {
				s.ScopedAgentSessionIDs = make(map[string]string)
			}
			s.ScopedAgentSessionIDs[scope] = id
		}
		s.AgentSessionScope = scope
	} else {
		s.AgentSessionScope = ""
	}

	s.AgentSessionID = id
	s.AgentType = agentType
}

func (s *Session) removeAgentSessionIDLocked(agentSessionID string) bool {
	agentSessionID = strings.TrimSpace(agentSessionID)
	if agentSessionID == "" {
		return false
	}

	removed := false
	if strings.TrimSpace(s.AgentSessionID) == agentSessionID {
		s.AgentSessionID = ""
		removed = true
	}
	if s.ScopedAgentSessionIDs != nil {
		for scope, id := range s.ScopedAgentSessionIDs {
			if strings.TrimSpace(id) != agentSessionID {
				continue
			}
			delete(s.ScopedAgentSessionIDs, scope)
			removed = true
		}
		if len(s.ScopedAgentSessionIDs) == 0 {
			s.ScopedAgentSessionIDs = nil
		}
	}
	if removed && s.AgentSessionScope != "" && s.AgentSessionID == "" {
		if s.ScopedAgentSessionIDs != nil {
			s.AgentSessionID = strings.TrimSpace(s.ScopedAgentSessionIDs[s.AgentSessionScope])
		}
		if s.AgentSessionID == "" {
			s.AgentSessionScope = ""
		}
	}
	return removed
}

// SetAgentInfo atomically sets the agent session ID, agent type, and name.
func (s *Session) SetAgentInfo(agentSessionID, agentType, name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.setScopedAgentSessionIDLocked("", agentSessionID, agentType)
	s.Name = name
}

// SetAgentInfoForScope atomically sets the scoped agent session ID, agent type,
// and display name for the active account/provider scope.
func (s *Session) SetAgentInfoForScope(scope, agentSessionID, agentType, name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.setScopedAgentSessionIDLocked(scope, agentSessionID, agentType)
	s.Name = name
}

// GetAgentSessionID atomically reads the agent session ID.
func (s *Session) GetAgentSessionID() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.AgentSessionID
}

// GetAgentSessionIDForScope atomically reads the agent session ID for a
// specific account/provider scope, falling back to legacy single-session state.
func (s *Session) GetAgentSessionIDForScope(scope string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.getScopedAgentSessionIDLocked(scope)
}

// GetResumeAgentSessionIDForScope returns the best backend-session candidate to
// resume for the given scope. It prefers an exact scoped binding, then falls
// back to the currently active binding, then any other known scoped binding.
func (s *Session) GetResumeAgentSessionIDForScope(scope string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.getResumeAgentSessionIDLocked(scope)
}

// GetName atomically reads the session name.
func (s *Session) GetName() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.Name
}

// SetAgentSessionID atomically sets the agent session ID and agent type.
func (s *Session) SetAgentSessionID(id, agentType string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.setScopedAgentSessionIDLocked("", id, agentType)
}

// SetAgentSessionIDForScope atomically sets the scoped agent session ID for the
// active account/provider scope.
func (s *Session) SetAgentSessionIDForScope(scope, id, agentType string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.setScopedAgentSessionIDLocked(scope, id, agentType)
}

// CompareAndSetAgentSessionID sets the agent session ID only if it is currently empty.
// Returns true if the value was set, false if it was already non-empty.
func (s *Session) CompareAndSetAgentSessionID(id, agentType string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.getScopedAgentSessionIDLocked("") != "" {
		return false
	}
	s.setScopedAgentSessionIDLocked("", id, agentType)
	return true
}

// CompareAndSetAgentSessionIDForScope sets the scoped agent session ID only if
// the given scope does not already have a bound backend session.
func (s *Session) CompareAndSetAgentSessionIDForScope(scope, id, agentType string) bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.getScopedAgentSessionIDLocked(scope) != "" {
		return false
	}
	s.setScopedAgentSessionIDLocked(scope, id, agentType)
	return true
}

// ActivateAgentSessionScope switches the active backend-session binding to the
// given account/provider scope and returns the bound agent session ID, if any.
func (s *Session) ActivateAgentSessionScope(scope string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	scope = normalizeSessionScope(scope)
	activeID := s.getScopedAgentSessionIDLocked(scope)
	s.AgentSessionScope = scope
	s.AgentSessionID = activeID
	return s.AgentSessionID
}

func (s *Session) ClearHistory() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.History = nil
}

// GetHistory returns the last n entries. If n <= 0, returns all.
func (s *Session) GetHistory(n int) []HistoryEntry {
	s.mu.Lock()
	defer s.mu.Unlock()
	total := len(s.History)
	if n <= 0 || n > total {
		n = total
	}
	out := make([]HistoryEntry, n)
	copy(out, s.History[total-n:])
	return out
}

// UserMeta stores human-readable display info for a session key.
type UserMeta struct {
	UserName string `json:"user_name,omitempty"`
	ChatName string `json:"chat_name,omitempty"`
}

// sessionSnapshot is the JSON-serializable state of the SessionManager.
type sessionSnapshot struct {
	Sessions      map[string]*Session  `json:"sessions"`
	ActiveSession map[string]string    `json:"active_session"`
	UserSessions  map[string][]string  `json:"user_sessions"`
	Counter       int64                `json:"counter"`
	SessionNames  map[string]string    `json:"session_names,omitempty"` // agent session ID → custom name
	UserMeta      map[string]*UserMeta `json:"user_meta,omitempty"`     // sessionKey → display info
	SharedSlots   map[string]string    `json:"shared_slots,omitempty"`  // sessionKey → shared slot binding
}

// SessionManager supports multiple named sessions per user with active-session tracking.
// It can persist state to a JSON file and reload on startup.
type SessionManager struct {
	mu            sync.RWMutex
	sessions      map[string]*Session
	activeSession map[string]string
	userSessions  map[string][]string
	sessionNames  map[string]string    // agent session ID → custom name
	userMeta      map[string]*UserMeta // sessionKey → display info
	sharedSlots   map[string]string    // sessionKey → shared slot binding
	counter       int64
	storePath     string // empty = no persistence
}

func NewSessionManager(storePath string) *SessionManager {
	sm := &SessionManager{
		sessions:      make(map[string]*Session),
		activeSession: make(map[string]string),
		userSessions:  make(map[string][]string),
		sessionNames:  make(map[string]string),
		userMeta:      make(map[string]*UserMeta),
		sharedSlots:   make(map[string]string),
		storePath:     storePath,
	}
	if storePath != "" {
		sm.load()
	}
	return sm
}

// StorePath returns the file path used for session persistence.
func (sm *SessionManager) StorePath() string {
	return sm.storePath
}

func (sm *SessionManager) nextID() string {
	sm.counter++
	return fmt.Sprintf("s%d", sm.counter)
}

func (sm *SessionManager) GetOrCreateActive(userKey string) *Session {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	if sid, ok := sm.activeSession[userKey]; ok {
		if s, ok := sm.sessions[sid]; ok {
			return s
		}
	}
	s := sm.createLocked(userKey, "default")
	sm.saveLocked()
	return s
}

func (sm *SessionManager) NewSession(userKey, name string) *Session {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	s := sm.createLocked(userKey, name)
	sm.saveLocked()
	return s
}

func (sm *SessionManager) createLocked(userKey, name string) *Session {
	id := sm.nextID()
	now := time.Now()
	s := &Session{
		ID:        id,
		Name:      name,
		CreatedAt: now,
		UpdatedAt: now,
	}
	sm.sessions[id] = s
	sm.activeSession[userKey] = id
	sm.userSessions[userKey] = append(sm.userSessions[userKey], id)
	return s
}

func (sm *SessionManager) SwitchSession(userKey, target string) (*Session, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	for _, sid := range sm.userSessions[userKey] {
		s := sm.sessions[sid]
		if s != nil && (s.ID == target || s.Name == target) {
			sm.activeSession[userKey] = s.ID
			sm.saveLocked()
			return s, nil
		}
	}
	return nil, fmt.Errorf("session %q not found", target)
}

func (sm *SessionManager) ListSessions(userKey string) []*Session {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	ids := sm.userSessions[userKey]
	out := make([]*Session, 0, len(ids))
	for _, sid := range ids {
		if s, ok := sm.sessions[sid]; ok {
			out = append(out, s)
		}
	}
	return out
}

func (sm *SessionManager) ActiveSessionID(userKey string) string {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.activeSession[userKey]
}

// SetSessionName sets a custom display name for an agent session.
func (sm *SessionManager) SetSessionName(agentSessionID, name string) {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	if name == "" {
		delete(sm.sessionNames, agentSessionID)
	} else {
		sm.sessionNames[agentSessionID] = name
	}
	sm.saveLocked()
}

// GetSessionName returns the custom name for an agent session, or "".
func (sm *SessionManager) GetSessionName(agentSessionID string) string {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.sessionNames[agentSessionID]
}

// UpdateUserMeta updates the human-readable metadata for a session key.
// Only non-empty fields are applied (merge behavior).
func (sm *SessionManager) UpdateUserMeta(sessionKey, userName, chatName string) {
	if userName == "" && chatName == "" {
		return
	}
	sm.mu.Lock()
	defer sm.mu.Unlock()
	meta, ok := sm.userMeta[sessionKey]
	if !ok {
		meta = &UserMeta{}
		sm.userMeta[sessionKey] = meta
	}
	if userName != "" {
		meta.UserName = userName
	}
	if chatName != "" {
		meta.ChatName = chatName
	}
}

// GetUserMeta returns a copy of the stored metadata for a session key, or nil.
func (sm *SessionManager) GetUserMeta(sessionKey string) *UserMeta {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	m := sm.userMeta[sessionKey]
	if m == nil {
		return nil
	}
	cp := *m
	return &cp
}

// SetSharedSlotBinding binds a platform session key to a shared slot.
func (sm *SessionManager) SetSharedSlotBinding(sessionKey, slot string) {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	slot = strings.TrimSpace(slot)
	if slot == "" {
		delete(sm.sharedSlots, sessionKey)
	} else {
		sm.sharedSlots[sessionKey] = slot
	}
	sm.saveLocked()
}

// GetSharedSlotBinding returns the currently bound shared slot for a platform session.
func (sm *SessionManager) GetSharedSlotBinding(sessionKey string) string {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return strings.TrimSpace(sm.sharedSlots[sessionKey])
}

// ClearSharedSlotBinding removes any shared slot binding for a platform session.
func (sm *SessionManager) ClearSharedSlotBinding(sessionKey string) {
	sm.SetSharedSlotBinding(sessionKey, "")
}

// AllSessions returns all sessions across all user keys.
func (sm *SessionManager) AllSessions() []*Session {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	out := make([]*Session, 0, len(sm.sessions))
	for _, s := range sm.sessions {
		out = append(out, s)
	}
	return out
}

// FindByID looks up a session by its internal ID across all users.
func (sm *SessionManager) FindByID(id string) *Session {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	return sm.sessions[id]
}

// DeleteByID removes a session by its internal ID from all tracking structures.
func (sm *SessionManager) DeleteByID(id string) bool {
	sm.mu.Lock()
	defer sm.mu.Unlock()
	if _, ok := sm.sessions[id]; !ok {
		return false
	}
	sm.deleteByIDLocked(id)
	sm.saveLocked()
	return true
}

// DeleteByAgentSessionID removes all local sessions mapped to the given
// agent session ID. It returns the number of removed local sessions.
func (sm *SessionManager) DeleteByAgentSessionID(agentSessionID string) int {
	if agentSessionID == "" {
		return 0
	}

	sm.mu.Lock()
	defer sm.mu.Unlock()

	removed := 0
	for _, s := range sm.sessions {
		s.mu.Lock()
		matched := s.removeAgentSessionIDLocked(agentSessionID)
		s.mu.Unlock()
		if !matched {
			continue
		}
		removed++
	}
	if removed > 0 {
		sm.saveLocked()
	}
	return removed
}

func (sm *SessionManager) deleteByIDLocked(id string) {
	delete(sm.sessions, id)
	for userKey, ids := range sm.userSessions {
		for i, sid := range ids {
			if sid == id {
				sm.userSessions[userKey] = append(ids[:i], ids[i+1:]...)
				break
			}
		}
		if sm.activeSession[userKey] == id {
			delete(sm.activeSession, userKey)
		}
	}
}

// Save persists current state to disk. Safe to call from outside (e.g. after message processing).
func (sm *SessionManager) Save() {
	sm.mu.RLock()
	defer sm.mu.RUnlock()
	sm.saveLocked()
}

func (sm *SessionManager) saveLocked() {
	if sm.storePath == "" {
		return
	}

	// Build a deep-copy snapshot to avoid racing with concurrent Session mutations.
	snapSessions := make(map[string]*Session, len(sm.sessions))
	for id, s := range sm.sessions {
		s.mu.Lock()
		snapSessions[id] = &Session{
			ID:                s.ID,
			Name:              s.Name,
			AgentSessionID:    s.AgentSessionID,
			AgentSessionScope: s.AgentSessionScope,
			AgentType:         s.AgentType,
			History:           append([]HistoryEntry(nil), s.History...),
			CreatedAt:         s.CreatedAt,
			UpdatedAt:         s.UpdatedAt,
		}
		if len(s.ScopedAgentSessionIDs) > 0 {
			snapSessions[id].ScopedAgentSessionIDs = make(map[string]string, len(s.ScopedAgentSessionIDs))
			for scope, sid := range s.ScopedAgentSessionIDs {
				snapSessions[id].ScopedAgentSessionIDs[scope] = sid
			}
		}
		s.mu.Unlock()
	}

	snap := sessionSnapshot{
		Sessions:      snapSessions,
		ActiveSession: sm.activeSession,
		UserSessions:  sm.userSessions,
		Counter:       sm.counter,
		SessionNames:  sm.sessionNames,
		UserMeta:      sm.userMeta,
		SharedSlots:   sm.sharedSlots,
	}
	data, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		slog.Error("session: failed to marshal", "error", err)
		return
	}
	if err := os.MkdirAll(filepath.Dir(sm.storePath), 0o755); err != nil {
		slog.Error("session: failed to create dir", "error", err)
		return
	}
	if err := AtomicWriteFile(sm.storePath, data, 0o644); err != nil {
		slog.Error("session: failed to write", "path", sm.storePath, "error", err)
	}
}

func (sm *SessionManager) load() {
	data, err := os.ReadFile(sm.storePath)
	if err != nil {
		if !os.IsNotExist(err) {
			slog.Error("session: failed to read", "path", sm.storePath, "error", err)
		}
		return
	}
	var snap sessionSnapshot
	if err := json.Unmarshal(data, &snap); err != nil {
		slog.Error("session: failed to unmarshal", "path", sm.storePath, "error", err)
		return
	}
	sm.sessions = snap.Sessions
	sm.activeSession = snap.ActiveSession
	sm.userSessions = snap.UserSessions
	sm.sessionNames = snap.SessionNames
	sm.userMeta = snap.UserMeta
	sm.sharedSlots = snap.SharedSlots
	sm.counter = snap.Counter

	if sm.sessions == nil {
		sm.sessions = make(map[string]*Session)
	}
	if sm.activeSession == nil {
		sm.activeSession = make(map[string]string)
	}
	if sm.userSessions == nil {
		sm.userSessions = make(map[string][]string)
	}
	if sm.sessionNames == nil {
		sm.sessionNames = make(map[string]string)
	}
	if sm.userMeta == nil {
		sm.userMeta = make(map[string]*UserMeta)
	}
	if sm.sharedSlots == nil {
		sm.sharedSlots = make(map[string]string)
	}

	slog.Info("session: loaded from disk", "path", sm.storePath, "sessions", len(sm.sessions))
}

// InvalidateForAgent clears AgentSessionID on all sessions whose AgentType
// does not match the current agent. This handles the case where the user
// switches agent types (e.g. opencode → pi) and stale session IDs from the
// old agent would cause errors.
func (sm *SessionManager) InvalidateForAgent(agentType string) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	invalidated := 0
	for _, s := range sm.sessions {
		s.mu.Lock()
		if s.AgentSessionID != "" && s.AgentType != "" && s.AgentType != agentType {
			slog.Info("session: invalidating stale agent session",
				"session", s.ID,
				"old_agent", s.AgentType,
				"new_agent", agentType,
				"old_agent_session_id", s.AgentSessionID,
			)
			s.AgentSessionID = ""
			s.AgentSessionScope = ""
			s.ScopedAgentSessionIDs = nil
			s.AgentType = agentType
			invalidated++
		}
		s.mu.Unlock()
	}
	if invalidated > 0 {
		sm.saveLocked()
	}
}
