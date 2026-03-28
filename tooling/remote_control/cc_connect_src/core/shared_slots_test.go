package core

import (
	"errors"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"
)

func TestSharedSlotManager_CreateAcquireReleaseLifecycle(t *testing.T) {
	now := time.Date(2026, 3, 27, 10, 0, 0, 0, time.UTC)
	manager := NewSharedSlotManager(filepath.Join(t.TempDir(), "shared"))
	manager.now = func() time.Time { return now }

	slot, err := manager.CreateSlot("/tmp/workspace-a", "debug", "remote")
	if err != nil {
		t.Fatalf("CreateSlot: %v", err)
	}
	if slot.Slot != "s001" {
		t.Fatalf("slot id = %q, want s001", slot.Slot)
	}

	lease, err := manager.AcquireLease("/tmp/workspace-a", slot.Slot, SharedSlotLeaseRequest{
		HolderType: "remote",
		HolderID:   "feishu:chat:user",
		HolderName: "feishu/chat",
	})
	if err != nil {
		t.Fatalf("AcquireLease: %v", err)
	}
	if lease.HolderID != "feishu:chat:user" {
		t.Fatalf("lease holder = %q, want feishu:chat:user", lease.HolderID)
	}

	_, err = manager.AcquireLease("/tmp/workspace-a", slot.Slot, SharedSlotLeaseRequest{
		HolderType: "local",
		HolderID:   "pid:123",
	})
	var busyErr *SharedSlotBusyError
	if !errors.As(err, &busyErr) {
		t.Fatalf("AcquireLease busy err = %v, want SharedSlotBusyError", err)
	}

	view, err := manager.GetSlot("/tmp/workspace-a", slot.Slot)
	if err != nil {
		t.Fatalf("GetSlot: %v", err)
	}
	if view.Lease == nil || view.Lease.HolderID != "feishu:chat:user" {
		t.Fatalf("GetSlot lease = %+v, want remote holder", view.Lease)
	}

	if err := manager.ReleaseLease("/tmp/workspace-a", slot.Slot, "remote", "feishu:chat:user", false); err != nil {
		t.Fatalf("ReleaseLease: %v", err)
	}
	view, err = manager.GetSlot("/tmp/workspace-a", slot.Slot)
	if err != nil {
		t.Fatalf("GetSlot after release: %v", err)
	}
	if view.Lease != nil {
		t.Fatalf("lease after release = %+v, want nil", view.Lease)
	}
}

func TestSharedSlotManager_LeaseExpiryAllowsReacquire(t *testing.T) {
	now := time.Date(2026, 3, 27, 10, 0, 0, 0, time.UTC)
	manager := NewSharedSlotManager(filepath.Join(t.TempDir(), "shared"))
	manager.now = func() time.Time { return now }

	slot, err := manager.CreateSlot("/tmp/workspace-b", "", "remote")
	if err != nil {
		t.Fatalf("CreateSlot: %v", err)
	}
	if _, err := manager.AcquireLease("/tmp/workspace-b", slot.Slot, SharedSlotLeaseRequest{
		HolderType: "remote",
		HolderID:   "feishu:chat:user",
	}); err != nil {
		t.Fatalf("AcquireLease remote: %v", err)
	}

	now = now.Add(DefaultSharedSlotLeaseTTL + time.Minute)

	lease, err := manager.AcquireLease("/tmp/workspace-b", slot.Slot, SharedSlotLeaseRequest{
		HolderType: "local",
		HolderID:   "pid:456",
	})
	if err != nil {
		t.Fatalf("AcquireLease local after expiry: %v", err)
	}
	if lease.HolderType != "local" || lease.HolderID != "pid:456" {
		t.Fatalf("lease after expiry = %+v, want local/pid:456", lease)
	}
}

func TestSharedSlotManager_UpdateSlotMetadata(t *testing.T) {
	manager := NewSharedSlotManager(filepath.Join(t.TempDir(), "shared"))
	slot, err := manager.CreateSlot("/tmp/workspace-c", "short", "local")
	if err != nil {
		t.Fatalf("CreateSlot: %v", err)
	}

	updated, err := manager.UpdateSlot("/tmp/workspace-c", slot.Slot, SharedSlotRecordUpdate{
		SessionID:    "sess_123",
		Title:        "renamed",
		ProviderName: "acc2",
		CodexHome:    "/tmp/.codex-acc2",
		UpdatedBy:    "remote",
	})
	if err != nil {
		t.Fatalf("UpdateSlot: %v", err)
	}
	if updated.SessionID != "sess_123" || updated.Title != "renamed" {
		t.Fatalf("updated slot = %+v, want session/title updated", updated)
	}

	view, err := manager.GetSlot("/tmp/workspace-c", slot.Slot)
	if err != nil {
		t.Fatalf("GetSlot: %v", err)
	}
	if view.Slot.ProviderName != "acc2" || view.Slot.CodexHome != "/tmp/.codex-acc2" {
		t.Fatalf("view slot = %+v, want provider/codex_home updated", view.Slot)
	}
}

func TestSharedSlotManager_LocalBindingPersistence(t *testing.T) {
	manager := NewSharedSlotManager(filepath.Join(t.TempDir(), "shared"))
	slot, err := manager.CreateSlot("/tmp/workspace-d", "debug", "local")
	if err != nil {
		t.Fatalf("CreateSlot: %v", err)
	}

	if err := manager.SetLocalBinding("/tmp/workspace-d", slot.Slot); err != nil {
		t.Fatalf("SetLocalBinding: %v", err)
	}

	bound, err := manager.GetLocalBinding("/tmp/workspace-d")
	if err != nil {
		t.Fatalf("GetLocalBinding: %v", err)
	}
	if bound != slot.Slot {
		t.Fatalf("local binding = %q, want %q", bound, slot.Slot)
	}

	manager2 := NewSharedSlotManager(manager.stateDir())
	bound, err = manager2.GetLocalBinding("/tmp/workspace-d")
	if err != nil {
		t.Fatalf("GetLocalBinding after reload: %v", err)
	}
	if bound != slot.Slot {
		t.Fatalf("local binding after reload = %q, want %q", bound, slot.Slot)
	}

	if err := manager2.ClearLocalBinding("/tmp/workspace-d"); err != nil {
		t.Fatalf("ClearLocalBinding: %v", err)
	}
	bound, err = manager2.GetLocalBinding("/tmp/workspace-d")
	if err != nil {
		t.Fatalf("GetLocalBinding after clear: %v", err)
	}
	if bound != "" {
		t.Fatalf("local binding after clear = %q, want empty", bound)
	}
}

func TestSharedSlotManager_DropsDeadLocalLease(t *testing.T) {
	manager := NewSharedSlotManager(filepath.Join(t.TempDir(), "shared"))
	slot, err := manager.CreateSlot("/tmp/workspace-e", "debug", "local")
	if err != nil {
		t.Fatalf("CreateSlot: %v", err)
	}

	deadPID := os.Getpid() + 100000000
	if _, err := manager.AcquireLease("/tmp/workspace-e", slot.Slot, SharedSlotLeaseRequest{
		HolderType: "local",
		HolderID:   "local:pid:" + strconv.Itoa(deadPID),
	}); err != nil {
		t.Fatalf("AcquireLease: %v", err)
	}

	view, err := manager.GetSlot("/tmp/workspace-e", slot.Slot)
	if err != nil {
		t.Fatalf("GetSlot: %v", err)
	}
	if view.Lease != nil {
		t.Fatalf("lease = %+v, want nil after dead local holder cleanup", view.Lease)
	}
}
