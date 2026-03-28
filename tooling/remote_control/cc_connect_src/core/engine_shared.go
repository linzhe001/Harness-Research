package core

import (
	"errors"
	"fmt"
	"os"
	"strings"
	"time"
)

func (e *Engine) sharedSlotManagerForSessions(sessions *SessionManager) *SharedSlotManager {
	storePath := ""
	if sessions != nil {
		storePath = sessions.StorePath()
	}
	return NewSharedSlotManager(SharedSessionStateDirFromStore(storePath))
}

func activeProviderMeta(agent Agent) (providerName, codexHome string) {
	if switcher, ok := agent.(ProviderSwitcher); ok {
		if active := switcher.GetActiveProvider(); active != nil {
			providerName = strings.TrimSpace(active.Name)
			codexHome = strings.TrimSpace(active.Env["CODEX_HOME"])
		}
	}
	if codexHome == "" {
		codexHome = strings.TrimSpace(os.Getenv("CODEX_HOME"))
	}
	return providerName, codexHome
}

func formatSharedSlotLease(lease *SharedSlotLease) string {
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
	return fmt.Sprintf("%s until %s", holder, lease.LeaseUntil.Format("2006-01-02 15:04"))
}

func formatSharedSlotView(view SharedSlotView, boundSlot string) string {
	label := view.Slot.Slot
	if view.Slot.Slot == boundSlot {
		label += " [bound]"
	}
	parts := []string{label}
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
	parts = append(parts, fmt.Sprintf("lease=%s", formatSharedSlotLease(view.Lease)))
	if view.Slot.Archived {
		parts = append(parts, "archived")
	}
	return "- " + strings.Join(parts, " | ")
}

func (e *Engine) remoteLeaseRequest(msg *Message) SharedSlotLeaseRequest {
	holderName := strings.TrimSpace(msg.Platform)
	if user := strings.TrimSpace(msg.UserName); user != "" {
		if holderName != "" {
			holderName += "/"
		}
		holderName += user
	}
	return SharedSlotLeaseRequest{
		HolderType: "remote",
		HolderID:   msg.SessionKey,
		HolderName: holderName,
		LeaseTTL:   DefaultSharedSlotLeaseTTL,
	}
}

func defaultSharedSlotTitle(session *Session) string {
	if session == nil {
		return ""
	}
	name := strings.TrimSpace(session.GetName())
	switch strings.ToLower(name) {
	case "", "default", "session":
		return ""
	default:
		return name
	}
}

func (e *Engine) releaseSharedSlotBinding(workspace string, manager *SharedSlotManager, sessions *SessionManager, holderType, holderID, slot string, clearBinding bool) {
	slot = strings.TrimSpace(slot)
	if slot == "" || manager == nil || sessions == nil {
		return
	}
	_ = manager.ReleaseLease(workspace, slot, holderType, holderID, false)
	if clearBinding {
		sessions.ClearSharedSlotBinding(holderID)
	}
}

func (e *Engine) bindFreshRemoteSharedSlot(msg *Message, sessions *SessionManager, manager *SharedSlotManager, workspace string, session *Session) (string, error) {
	title := defaultSharedSlotTitle(session)
	slot, err := manager.CreateSlot(workspace, title, "remote-auto")
	if err != nil {
		return "", err
	}
	if _, err := manager.AcquireLease(workspace, slot.Slot, e.remoteLeaseRequest(msg)); err != nil {
		return "", err
	}
	sessions.SetSharedSlotBinding(msg.SessionKey, slot.Slot)
	return slot.Slot, nil
}

func (e *Engine) ensureDefaultSharedSlot(msg *Message, sessions *SessionManager, agent Agent, session *Session, manager *SharedSlotManager, workspace string) (string, error) {
	slot := strings.TrimSpace(sessions.GetSharedSlotBinding(msg.SessionKey))
	if slot != "" {
		return slot, nil
	}

	slot, err := e.bindFreshRemoteSharedSlot(msg, sessions, manager, workspace, session)
	if err != nil {
		return "", err
	}

	providerName, codexHome := activeProviderMeta(agent)
	update := SharedSlotRecordUpdate{
		ProviderName: providerName,
		CodexHome:    codexHome,
		UpdatedBy:    "remote-auto",
	}
	if sessionID := strings.TrimSpace(session.GetResumeAgentSessionIDForScope(currentSessionScope(agent))); sessionID != "" {
		update.SessionID = sessionID
	}
	_, _ = manager.UpdateSlot(workspace, slot, update)
	return slot, nil
}

func (e *Engine) ensureBoundSharedSlot(msg *Message, sessions *SessionManager, agent Agent, session *Session) error {
	if sessions == nil || agent == nil || session == nil || msg == nil {
		return nil
	}
	workspace := e.workspaceDirForSessionKey(msg.SessionKey)
	manager := e.sharedSlotManagerForSessions(sessions)
	slot, err := e.ensureDefaultSharedSlot(msg, sessions, agent, session, manager, workspace)
	if err != nil {
		return err
	}
	view, err := manager.GetSlot(workspace, slot)
	if err != nil {
		return fmt.Errorf("shared slot %s unavailable: %w", slot, err)
	}
	if _, err := manager.AcquireLease(workspace, slot, e.remoteLeaseRequest(msg)); err != nil {
		return err
	}

	scope := currentSessionScope(agent)
	if sessionID := strings.TrimSpace(view.Slot.SessionID); sessionID != "" {
		session.SetAgentInfoForScope(scope, sessionID, agent.Name(), view.Slot.Title)
	}

	providerName, codexHome := activeProviderMeta(agent)
	_, _ = manager.UpdateSlot(workspace, slot, SharedSlotRecordUpdate{
		ProviderName: providerName,
		CodexHome:    codexHome,
		UpdatedBy:    "remote",
	})
	return nil
}

func (e *Engine) syncBoundSharedSlot(sessionKey string, sessions *SessionManager, agent Agent, sessionID string) {
	if sessions == nil || agent == nil {
		return
	}
	slot := sessions.GetSharedSlotBinding(sessionKey)
	if slot == "" {
		return
	}
	sessionID = strings.TrimSpace(sessionID)
	if sessionID == "" {
		return
	}
	workspace := e.workspaceDirForSessionKey(sessionKey)
	providerName, codexHome := activeProviderMeta(agent)
	manager := e.sharedSlotManagerForSessions(sessions)
	_, _ = manager.UpdateSlot(workspace, slot, SharedSlotRecordUpdate{
		SessionID:    sessionID,
		ProviderName: providerName,
		CodexHome:    codexHome,
		UpdatedBy:    "remote",
	})
}

func (e *Engine) cmdShared(p Platform, msg *Message, args []string) {
	agent, sessions, interactiveKey, err := e.commandContext(p, msg)
	if err != nil {
		e.reply(p, msg.ReplyCtx, fmt.Sprintf(e.i18n.T(MsgError), err))
		return
	}
	workspace := e.commandWorkspaceDir(msg)
	manager := e.sharedSlotManagerForSessions(sessions)
	currentSlot := sessions.GetSharedSlotBinding(msg.SessionKey)

	sub := "status"
	if len(args) > 0 {
		sub = strings.ToLower(strings.TrimSpace(args[0]))
	}

	switch matchSubCommand(sub, []string{"list", "new", "use", "status", "release", "detach"}) {
	case "list":
		views, err := manager.ListSlots(workspace)
		if err != nil {
			e.reply(p, msg.ReplyCtx, fmt.Sprintf(e.i18n.T(MsgError), err))
			return
		}
		if len(views) == 0 {
			e.reply(p, msg.ReplyCtx, "No shared slots for this workspace.")
			return
		}
		lines := []string{fmt.Sprintf("Shared slots for `%s`:", workspace)}
		for _, view := range views {
			lines = append(lines, formatSharedSlotView(view, currentSlot))
		}
		e.reply(p, msg.ReplyCtx, strings.Join(lines, "\n"))

	case "new":
		title := strings.TrimSpace(strings.Join(args[1:], " "))
		if currentSlot != "" {
			e.releaseSharedSlotBinding(workspace, manager, sessions, "remote", msg.SessionKey, currentSlot, false)
		}
		slot, err := manager.CreateSlot(workspace, title, "remote")
		if err != nil {
			e.reply(p, msg.ReplyCtx, fmt.Sprintf(e.i18n.T(MsgError), err))
			return
		}
		if _, err := manager.AcquireLease(workspace, slot.Slot, e.remoteLeaseRequest(msg)); err != nil {
			e.reply(p, msg.ReplyCtx, fmt.Sprintf(e.i18n.T(MsgError), err))
			return
		}
		e.cleanupInteractiveState(interactiveKey)
		sessions.SetSharedSlotBinding(msg.SessionKey, slot.Slot)
		session := sessions.GetOrCreateActive(msg.SessionKey)
		e.resetConversationState(session, sessions, agent)
		e.reply(p, msg.ReplyCtx, fmt.Sprintf("Shared slot `%s` is ready. Send your next message to start the session.", slot.Slot))

	case "use":
		if len(args) < 2 {
			e.reply(p, msg.ReplyCtx, "Usage: /shared use <slot>")
			return
		}
		slotID := strings.TrimSpace(args[1])
		view, err := manager.GetSlot(workspace, slotID)
		if err != nil {
			e.reply(p, msg.ReplyCtx, fmt.Sprintf(e.i18n.T(MsgError), err))
			return
		}
		lease, err := manager.AcquireLease(workspace, slotID, e.remoteLeaseRequest(msg))
		if err != nil {
			e.reply(p, msg.ReplyCtx, fmt.Sprintf(e.i18n.T(MsgError), err))
			return
		}
		if currentSlot != "" && currentSlot != slotID {
			e.releaseSharedSlotBinding(workspace, manager, sessions, "remote", msg.SessionKey, currentSlot, false)
		}
		e.cleanupInteractiveState(interactiveKey)
		sessions.SetSharedSlotBinding(msg.SessionKey, slotID)
		session := sessions.GetOrCreateActive(msg.SessionKey)
		e.resetConversationState(session, sessions, agent)
		if sessionID := strings.TrimSpace(view.Slot.SessionID); sessionID != "" {
			session.SetAgentInfoForScope(currentSessionScope(agent), sessionID, agent.Name(), view.Slot.Title)
			sessions.Save()
		}
		e.reply(p, msg.ReplyCtx, fmt.Sprintf("Attached shared slot `%s`. Lease: %s", slotID, formatSharedSlotLease(lease)))

	case "status":
		if currentSlot == "" {
			e.reply(p, msg.ReplyCtx, "No shared slot is currently bound to this chat.")
			return
		}
		view, err := manager.GetSlot(workspace, currentSlot)
		if err != nil {
			e.reply(p, msg.ReplyCtx, fmt.Sprintf(e.i18n.T(MsgError), err))
			return
		}
		lines := []string{
			fmt.Sprintf("Shared slot: `%s`", view.Slot.Slot),
			fmt.Sprintf("Lease: %s", formatSharedSlotLease(view.Lease)),
		}
		if title := strings.TrimSpace(view.Slot.Title); title != "" {
			lines = append(lines, fmt.Sprintf("Title: %s", title))
		}
		if sessionID := strings.TrimSpace(view.Slot.SessionID); sessionID != "" {
			lines = append(lines, fmt.Sprintf("Session: %s", sessionID))
		}
		if provider := strings.TrimSpace(view.Slot.ProviderName); provider != "" {
			lines = append(lines, fmt.Sprintf("Provider: %s", provider))
		}
		e.reply(p, msg.ReplyCtx, strings.Join(lines, "\n"))

	case "release":
		if currentSlot == "" {
			e.reply(p, msg.ReplyCtx, "No shared slot is currently bound to this chat.")
			return
		}
		e.cleanupInteractiveState(interactiveKey)
		if err := manager.ReleaseLease(workspace, currentSlot, "remote", msg.SessionKey, false); err != nil {
			e.reply(p, msg.ReplyCtx, fmt.Sprintf(e.i18n.T(MsgError), err))
			return
		}
		e.reply(p, msg.ReplyCtx, fmt.Sprintf("Released shared slot `%s`. The binding is kept for automatic resume.", currentSlot))

	case "detach":
		if currentSlot == "" {
			e.reply(p, msg.ReplyCtx, "No shared slot is currently bound to this chat.")
			return
		}
		e.cleanupInteractiveState(interactiveKey)
		e.releaseSharedSlotBinding(workspace, manager, sessions, "remote", msg.SessionKey, currentSlot, false)
		sessions.ClearSharedSlotBinding(msg.SessionKey)
		e.reply(p, msg.ReplyCtx, fmt.Sprintf("Detached shared slot `%s` from this chat.", currentSlot))

	default:
		e.reply(p, msg.ReplyCtx, "Usage: /shared <list|new|use|status|release|detach>")
	}
}

func formatSharedSlotBusy(err error) string {
	var busyErr *SharedSlotBusyError
	if errors.As(err, &busyErr) {
		return busyErr.Error()
	}
	return err.Error()
}

func formatSharedSlotAutoAttachError(err error) string {
	if err == nil {
		return ""
	}
	return fmt.Sprintf("Shared slot attach failed: %s", formatSharedSlotBusy(err))
}

func formatLeaseRemaining(lease *SharedSlotLease, now time.Time) string {
	if lease == nil {
		return "free"
	}
	remaining := lease.LeaseUntil.Sub(now).Round(time.Minute)
	if remaining < 0 {
		remaining = 0
	}
	return fmt.Sprintf("%s (%s remaining)", formatSharedSlotLease(lease), remaining)
}
