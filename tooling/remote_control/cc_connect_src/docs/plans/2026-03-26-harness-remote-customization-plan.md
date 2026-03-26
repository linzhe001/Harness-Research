# Harness Remote Customization Plan

**Date:** 2026-03-26
**Status:** Draft
**Target Repo:** `tooling/remote_control/cc_connect_src`

**Phase 1 Checklist:** `docs/plans/2026-03-26-harness-remote-customization-phase1.md`

## Goal

Make `cc-connect` work as the long-term remote control surface for `Harness-Research`, with four concrete outcomes:

1. `/home` and related cards become truly customizable, instead of being hardcoded or split across multiple rendering paths.
2. Codex account switching supports both:
   - manual switching from chat
   - automatic failover when the current account hits quota / rate limit
3. Codex model policy defaults to `gpt-5.4` and reasoning defaults to `xhigh`, with controlled fallback when the target model is unavailable.
4. Cards become actionable:
   - provider / model / reasoning should be switchable from the card itself when the platform callback works
   - if interactive submission is unavailable or unreliable, the card must still show copyable slash commands so the user can complete the action quickly

## Current Baseline

The current bundled source tree already contains a partial Harness-specific `/home` implementation:

- `/home` command entry exists in `core/engine.go`
- `renderHomeCard()` exists and loads `tooling/remote_control/scripts/harness_remote.sh summary --json`
- grouped help cards (`/help workspace`, `/help auto`, etc.) already exist
- Feishu card navigation callbacks already exist

However, the current behavior still has important gaps:

1. **Card customization is not configurable**
   - `remote_control.local.yaml` only stores default paths
   - card layout and labels are still hardcoded in `core/engine.go`

2. **Interactive Codex account failover is missing**
   - `cc-connect` supports `/provider switch <name>`
   - but ordinary chat sessions do not auto-switch after quota errors

3. **Model policy is only static**
   - fixed `model` / `reasoning_effort` values can be configured
   - there is no policy layer like “prefer `gpt-5.4`, fallback to next allowed model”

4. **Card affordance is incomplete**
   - provider / model / reasoning cards already render `select_static`
   - but the UX is weak when users do not realize that selecting triggers an immediate callback
   - when callbacks fail or are disabled, the user needs explicit copyable commands

## Design Decisions

### 1. Separate Data Plane and Presentation Plane

The `tooling/remote_control/` wrapper should remain the data plane:

- workspace summary
- auto-iterate status
- recommended actions
- logs / events

The bundled `cc-connect` source should own the presentation plane:

- card layout
- button / select behavior
- fallback command hints
- platform-specific interaction details

**Decision:** do not turn `tooling/remote_control/config/remote_control.local.yaml` into a card template file.  
That file should remain workspace-local runtime config. Card customization belongs in `cc-connect`.

### 2. Keep Manual Switching as the Lowest-Risk Escape Hatch

Even after automatic account switching is added, the user must always have a manual override path:

- `/provider`
- `/provider list`
- `/provider switch <name>`
- optional Chinese aliases for common accounts

Automatic switching should never remove the manual path.

### 3. Prefer “Immediate Apply + Visible Fallback” Over Multi-Step Submit Flows

The current card system already supports select-driven actions through Feishu callbacks.
For the first usable version:

- selection should apply immediately on supported platforms
- cards must explicitly say “selection applies immediately”
- cards must also show copyable slash commands

This is lower risk than introducing a second “submit” button flow everywhere.

If later testing shows users strongly prefer form-submit semantics, that can be a second iteration.

## Workstream A: Customizable Harness Cards

### Goal

Make `/home` and related cards customizable without hardcoding all labels, fields, and action rows in `core/engine.go`.

### Proposed Approach

Add a Harness-specific card config block in `cc-connect` project config, for example:

```toml
[projects.harness_cards]
enabled = true
home_title = "Harness 工作台"
show_workspace_root = true
show_metric = true
show_account = true
show_recommended_actions = true
show_copyable_commands = true
provider_card_show_copyable_commands = true
model_card_show_copyable_commands = true
reasoning_card_show_copyable_commands = true
```

### Why This Direction

- keeps card presentation in the UI layer (`cc-connect`)
- avoids coupling card UI to workspace YAML
- remains compatible with existing `summary --json` data contract

### Files

- Modify: `core/engine.go`
- Modify: `config/config.go`
- Modify: `config.example.toml`
- Modify: `core/i18n.go`
- Modify: `core/engine_test.go`

### Acceptance Criteria

- `/home` title, sections, and optional fields are configurable
- `/home` still works when the config block is absent
- `/home` keeps using `summary --json` as the data source
- grouped help cards stay compatible with the new `/home`

## Workstream B: Codex Account Auto Failover + Manual Switching

### Goal

Add interactive-session provider failover for Codex, while preserving manual switching.

### Current Gap

Today, quota failure in a normal chat session becomes `EventError`, but the engine only reports the error back to the user and stops the turn.

### Proposed Runtime Behavior

When a Codex session fails with a quota/rate-limit style error:

1. Detect the error as a provider exhaustion event.
2. Mark the current provider/account as cooling down.
3. Choose the next eligible provider according to config order / priority.
4. Switch provider.
5. Clear the current agent session ID so the next turn starts fresh under the new provider.
6. Send a user-facing message such as:
   - `已切换到 codex_secondary，请重发上一条消息。`

### V1 Safety Rule

Do **not** auto-resend the failed user prompt in the first version.

Reasons:

- avoids hidden duplicate execution
- avoids re-running shell / write actions unexpectedly
- reduces coordination bugs with interactive session state

### Config Additions

Extend provider config with optional runtime hints:

```toml
[[projects.agent.providers]]
name = "codex_primary"
priority = 100
cooldown_sec = 1800
auto_failover = true
env = { CODEX_HOME = "/home/user/.codex-acc1" }
```

### Implementation Shape

Prefer a small engine-owned provider runtime state helper:

- current provider
- cooldown-until timestamps
- next-provider selection

This should live in `core/`, not `agent/codex`, because provider selection is orchestration logic rather than Codex protocol logic.

### Files

- Modify: `core/interfaces.go` (only if helper interfaces need extension)
- Create: `core/provider_failover.go`
- Create: `core/provider_failover_test.go`
- Modify: `core/engine.go`
- Modify: `core/i18n.go`
- Modify: `config/config.go`
- Modify: `config.example.toml`
- Modify: `core/engine_test.go`

### Acceptance Criteria

- `/provider switch <name>` still works
- when the active Codex account hits quota, the next eligible account is selected automatically
- the user is informed which account was selected
- manual switching can still force a specific provider
- cooldown prevents immediate oscillation back to the exhausted provider

## Workstream C: Model Policy Defaults (`gpt-5.4` + `xhigh`)

### Goal

Make Codex default to the desired model/reasoning policy automatically, instead of relying on manual card clicks after startup.

### Current Baseline

The Codex agent already supports:

- `model`
- `reasoning_effort`
- runtime model switching
- runtime reasoning switching

But it lacks a policy layer that says:

- prefer `gpt-5.4`
- prefer `xhigh`
- fallback cleanly if the preferred model is unavailable

### Proposed Policy

Add explicit preference fields:

```toml
[projects.agent.options]
model = "gpt-5.4"
reasoning_effort = "xhigh"
preferred_models = ["gpt-5.4", "gpt-5.4-codex", "gpt-5.3-codex", "o3"]
```

Behavior:

1. If `model` is explicitly set and is valid, use it.
2. Otherwise, evaluate `preferred_models` in order.
3. Pick the first model that exists in `AvailableModels()`.
4. If none match, fall back to current behavior.
5. Apply `reasoning_effort = "xhigh"` by default unless explicitly overridden.

### Important Note

The exact model identifier must follow what Codex CLI actually exposes for the installed version.
Implementation should not hardcode only one label without fallback.

### Files

- Modify: `agent/codex/codex.go`
- Modify: `agent/codex/codex_model_test.go`
- Modify: `config/config.go`
- Modify: `config.example.toml`
- Modify: `docs/usage.md`
- Modify: `docs/usage.zh-CN.md`

### Acceptance Criteria

- a fresh Codex session defaults to the desired model policy
- reasoning defaults to `xhigh`
- fallback behavior is deterministic and test-covered
- provider switching does not silently drop the preferred model policy

## Workstream D: Card Interaction UX and Fallback Commands

### Goal

Make cards practical for real users, not just readable.

### Current Problem

Provider / model / reasoning cards already expose select options, but the user may not realize:

- selection already triggers a callback
- there is no separate “submit” button
- when callback delivery breaks, the card becomes read-only

### Proposed UX Rules

For provider / model / reasoning / home cards:

1. Show the current active value clearly.
2. If interactive selection is available:
   - keep `select_static`
   - add a visible note such as `选择后立即生效；如无反应，请复制下方命令`
3. Always render a copyable command block under the card:
   - provider:
     - `/provider switch codex_primary`
     - `/provider switch codex_secondary`
   - model:
     - `/model gpt-5.4`
   - reasoning:
     - `/reasoning xhigh`
4. If a platform does not support card navigation:
   - render the same information as plain text with commands

### Why Not Force a Submit Button First

Feishu already supports immediate callback on selection. Introducing a custom submit flow across cards adds complexity without being required for the first useful version.

The better first step is:

- make immediate behavior explicit
- add strong command fallback

### Files

- Modify: `core/engine.go`
- Modify: `core/i18n.go`
- Modify: `platform/feishu/card.go` (only if specific visual treatment is needed)
- Modify: `core/engine_test.go`
- Modify: `platform/feishu/platform_test.go`

### Acceptance Criteria

- provider / model / reasoning cards all show copyable commands
- cards explain whether selection is immediate
- when callback works, selection changes take effect
- when callback fails or platform lacks card support, the user still has usable commands

## Recommended Delivery Order

### Phase 0: Build and Run the Fork

Before new functional work:

- compile the current `tooling/remote_control/cc_connect_src` tree
- run it instead of the official prebuilt binary
- verify the existing `/home` and grouped help card behavior

### Phase 1: Card UX Baseline

- finish copyable command fallback for provider / model / reasoning / home cards
- add explicit “selection applies immediately” notes
- stabilize `/home` as the main entry card

### Phase 2: Provider Failover

- add quota/rate-limit detection
- add provider cooldown runtime state
- add automatic switch + user notification
- keep manual `/provider switch` as override

### Phase 3: Model Policy

- add preferred-model fallback chain
- default reasoning to `xhigh`
- verify provider switching preserves model policy

### Phase 4: Card Customization Config

- add `[projects.harness_cards]`
- make `/home` layout configurable
- add tests and config docs

## Testing Plan

At minimum, add tests for:

- `/home` card rendering with and without Harness card config
- provider card includes copyable commands
- model card includes copyable commands
- reasoning card includes copyable commands
- auto-switch occurs on quota-like `EventError`
- manual switch still works while cooldown state exists
- model policy resolves `gpt-5.4` if available, otherwise falls back deterministically
- Feishu callback still updates cards in place after these changes

## Risks

1. **Card and platform coupling**
   - Feishu supports richer interaction than some other platforms.
   - The design must keep text fallback first-class.

2. **Auto-resend hazards**
   - Automatically replaying failed user prompts is risky.
   - V1 should switch provider and ask the user to resend.

3. **Model naming drift**
   - Codex CLI model names may change across versions.
   - Fallback chains and tests are required.

4. **State split across repos**
   - `cc-connect` owns presentation
   - `tooling/remote_control` owns workspace summary data
   - the JSON contract between them must remain stable

## Definition of Done

This plan is complete when:

- `/home` is the primary actionable workspace card
- cards can either perform the action directly or present a copyable command fallback
- interactive Codex sessions can fail over to the next account on quota exhaustion
- manual provider switching remains available at all times
- Codex defaults to the desired model/reasoning policy with deterministic fallback
- the bundled source can be built and run as the actual binary used by the Harness workflow
