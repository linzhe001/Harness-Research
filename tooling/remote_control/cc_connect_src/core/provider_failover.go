package core

import (
	"sort"
	"strings"
	"sync"
	"time"
)

const defaultProviderCooldown = 30 * time.Minute

type providerFailoverRuntime struct {
	mu            sync.Mutex
	cooldownUntil map[string]time.Time
}

func newProviderFailoverRuntime() *providerFailoverRuntime {
	return &providerFailoverRuntime{
		cooldownUntil: make(map[string]time.Time),
	}
}

func providerAutoFailoverEnabled(p ProviderConfig) bool {
	if p.AutoFailover == nil {
		return true
	}
	return *p.AutoFailover
}

func providerCooldownDuration(p ProviderConfig) time.Duration {
	if p.CooldownSec > 0 {
		return time.Duration(p.CooldownSec) * time.Second
	}
	return defaultProviderCooldown
}

func IsProviderExhaustionError(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(strings.TrimSpace(err.Error()))
	if msg == "" {
		return false
	}
	patterns := []string{
		"quota",
		"insufficient_quota",
		"rate limit",
		"rate-limit",
		"rate_limit",
		"too many requests",
		"usage limit",
		"limit reached",
		"limit exceeded",
		"resource exhausted",
		"http 429",
		"status code: 429",
		"status=429",
	}
	for _, pattern := range patterns {
		if strings.Contains(msg, pattern) {
			return true
		}
	}
	return false
}

func (r *providerFailoverRuntime) Clear(name string) {
	if strings.TrimSpace(name) == "" {
		return
	}
	r.mu.Lock()
	delete(r.cooldownUntil, name)
	r.mu.Unlock()
}

func (r *providerFailoverRuntime) MarkCooldown(name string, until time.Time) {
	if strings.TrimSpace(name) == "" {
		return
	}
	r.mu.Lock()
	r.cooldownUntil[name] = until
	r.mu.Unlock()
}

func (r *providerFailoverRuntime) CooldownUntil(name string) time.Time {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.cooldownUntil[name]
}

func (r *providerFailoverRuntime) IsCoolingDown(name string, now time.Time) bool {
	if strings.TrimSpace(name) == "" {
		return false
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	until, ok := r.cooldownUntil[name]
	if !ok {
		return false
	}
	if until.After(now) {
		return true
	}
	delete(r.cooldownUntil, name)
	return false
}

type providerCandidate struct {
	Provider ProviderConfig
	Index    int
}

func orderedProviderCandidates(providers []ProviderConfig, currentName string) []providerCandidate {
	candidates := make([]providerCandidate, 0, len(providers))
	for idx, provider := range providers {
		candidates = append(candidates, providerCandidate{Provider: provider, Index: idx})
	}

	hasPriority := false
	for _, candidate := range candidates {
		if candidate.Provider.Priority != 0 {
			hasPriority = true
			break
		}
	}
	if hasPriority {
		sort.SliceStable(candidates, func(i, j int) bool {
			if candidates[i].Provider.Priority == candidates[j].Provider.Priority {
				return candidates[i].Index < candidates[j].Index
			}
			return candidates[i].Provider.Priority > candidates[j].Provider.Priority
		})
		return candidates
	}

	currentIdx := -1
	for idx, provider := range providers {
		if provider.Name == currentName {
			currentIdx = idx
			break
		}
	}
	if currentIdx <= -1 || len(candidates) <= 1 {
		return candidates
	}

	rotated := make([]providerCandidate, 0, len(candidates))
	for offset := 1; offset <= len(providers); offset++ {
		idx := (currentIdx + offset) % len(providers)
		rotated = append(rotated, providerCandidate{Provider: providers[idx], Index: idx})
	}
	return rotated
}

func (r *providerFailoverRuntime) NextProvider(providers []ProviderConfig, currentName string, now time.Time) *ProviderConfig {
	for _, candidate := range orderedProviderCandidates(providers, currentName) {
		name := strings.TrimSpace(candidate.Provider.Name)
		if name == "" || name == currentName {
			continue
		}
		if !providerAutoFailoverEnabled(candidate.Provider) {
			continue
		}
		if r.IsCoolingDown(name, now) {
			continue
		}
		provider := candidate.Provider
		return &provider
	}
	return nil
}
