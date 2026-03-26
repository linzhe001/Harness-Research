package core

import (
	"errors"
	"testing"
	"time"
)

func TestIsProviderExhaustionError(t *testing.T) {
	tests := []struct {
		err  error
		want bool
	}{
		{err: errors.New("429 Too Many Requests"), want: true},
		{err: errors.New("insufficient_quota"), want: true},
		{err: errors.New("rate limit reached for this account"), want: true},
		{err: errors.New("connection reset by peer"), want: false},
		{err: nil, want: false},
	}

	for _, tt := range tests {
		if got := IsProviderExhaustionError(tt.err); got != tt.want {
			t.Fatalf("IsProviderExhaustionError(%v) = %v, want %v", tt.err, got, tt.want)
		}
	}
}

func TestProviderFailoverRuntime_NextProviderSkipsCoolingProvider(t *testing.T) {
	runtime := newProviderFailoverRuntime()
	now := time.Now()
	runtime.MarkCooldown("secondary", now.Add(10*time.Minute))

	next := runtime.NextProvider([]ProviderConfig{
		{Name: "primary"},
		{Name: "secondary"},
		{Name: "tertiary"},
	}, "primary", now)

	if next == nil || next.Name != "tertiary" {
		t.Fatalf("next provider = %#v, want tertiary", next)
	}
}

func TestProviderFailoverRuntime_UsesPriorityWhenConfigured(t *testing.T) {
	runtime := newProviderFailoverRuntime()
	now := time.Now()

	next := runtime.NextProvider([]ProviderConfig{
		{Name: "primary", Priority: 10},
		{Name: "secondary", Priority: 50},
		{Name: "tertiary", Priority: 40},
	}, "primary", now)

	if next == nil || next.Name != "secondary" {
		t.Fatalf("next provider = %#v, want secondary", next)
	}
}
