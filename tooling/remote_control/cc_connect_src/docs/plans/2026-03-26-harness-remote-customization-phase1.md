# Harness Remote Customization Phase 1

**Date:** 2026-03-26
**Status:** Draft
**Parent Plan:** `docs/plans/2026-03-26-harness-remote-customization-plan.md`

## Goal

Deliver the first usable version of the Harness-specific `cc-connect` build by focusing on:

1. running the patched binary instead of the official prebuilt binary
2. stabilizing `/home` as the primary entry card
3. making provider / model / reasoning cards actionable in practice
4. adding clear copyable command fallback when GUI interaction is unavailable or unclear

This phase does **not** yet implement automatic account failover or model policy fallback chains. Those belong to later phases.

## Success Criteria

At the end of Phase 1:

- `/home` comes from the patched `cc-connect` binary, not the custom exec fallback
- `/home` card clearly shows workspace, loop status, account, metric, and recommended actions
- provider / model / reasoning cards all show:
  - current active value
  - immediate-apply interaction hint
  - copyable slash commands
- Feishu users can finish every critical switch operation even if card callback UX is confusing

## Task 0: Build and Run the Fork

### Files

- Existing source tree: `tooling/remote_control/cc_connect_src`
- Existing local launcher target:
  - `tooling/remote_control/bin/cc-connect`
  - `tooling/remote_control/vendor/bin/...`

### Work

1. Install Go 1.22+ on the machine.
2. Build the patched binary from `tooling/remote_control/cc_connect_src`.
3. Replace the current repo-local launcher target with the patched binary.
4. Start `cc-connect` with the existing:
   - `tooling/remote_control/config/cc_connect.local.toml`
5. Verify:
   - `/help`
   - `/help auto`
   - `/home`

### Acceptance

- `/home` no longer shows “不是 cc-connect 命令，已转发给 Agent 处理”
- `/home` button navigation works with the patched binary

## Task 1: Add Harness Card Config Block

### Goal

Introduce a small config surface for Harness card presentation, without making the system depend on workspace YAML.

### Files

- Modify: `config/config.go`
- Modify: `config.example.toml`
- Modify: `core/engine.go`

### Config Shape

Add an optional block under each project:

```toml
[projects.harness_cards]
enabled = true
home_title = "Harness 工作台"
show_workspace_root = true
show_metric = true
show_account = true
show_recommended_actions = true
show_copyable_commands = true
interaction_hint = "选择后立即生效；如无反应，请复制下方命令"
```

### Implementation Notes

- Keep all fields optional.
- Default behavior must match current behavior if the block is absent.
- This config only changes presentation, not remote wrapper behavior.

### Acceptance

- engine can read Harness card config
- `/home` title and optional sections can be toggled without changing `tooling/remote_control`

## Task 2: Extract Reusable Card Command Fallback Rendering

### Goal

Avoid duplicating “copyable commands” logic across provider / model / reasoning / home cards.

### Files

- Modify: `core/engine.go`
- Modify: `core/i18n.go`
- Modify: `core/engine_test.go`

### Work

Add a helper in `core/engine.go`, for example:

- `renderCardCommandFallback(title string, commands []string) string`
- or `appendCommandFallback(cb *CardBuilder, commands []string, hint string)`

The helper should:

- render a short explanatory note
- render commands as backtick-wrapped slash commands
- be safe on card and text fallback paths

### Acceptance

- a single helper is reused by provider / model / reasoning / home cards
- fallback commands are visible in rendered card text

## Task 3: Improve Provider Card

### Goal

Make the provider card operational, not just informational.

### Current State

`renderProviderCard()` already exposes a select widget, but it does not make the fallback command path explicit.

### Files

- Modify: `core/engine.go`
- Modify: `core/i18n.go`
- Modify: `core/engine_test.go`

### Work

Update `renderProviderCard()` to include:

1. current provider summary
2. immediate-apply note:
   - `选择后立即生效；如无反应，请复制下方命令`
3. copyable commands for each provider, e.g.:
   - `/provider switch codex_primary`
   - `/provider switch codex_secondary`
   - `/provider switch codex_tertiary`

### Tests

Add a test that verifies:

- current provider appears in rendered text
- at least one `/provider switch ...` command appears
- existing select widget still exists

### Acceptance

- users can switch provider by card interaction or by copied command

## Task 4: Improve Model Card

### Goal

Make model switching explicit and copyable.

### Files

- Modify: `core/engine.go`
- Modify: `core/i18n.go`
- Modify: `core/engine_test.go`

### Work

Update `renderModelCard()` to include:

1. current model
2. immediate-apply note
3. copyable commands such as:
   - `/model gpt-5.4`
   - `/model gpt-5.4-codex`
   - `/model o3`

Prefer the actual model identifiers exposed by `AvailableModels()`.

### Tests

Add a test that verifies:

- current model is rendered
- at least one `/model ...` command appears
- select widget still exists

### Acceptance

- model card is usable even if the callback flow is unclear to the user

## Task 5: Improve Reasoning Card

### Goal

Make reasoning selection explicit and copyable.

### Files

- Modify: `core/engine.go`
- Modify: `core/i18n.go`
- Modify: `core/engine_test.go`

### Work

Update `renderReasoningCard()` to include:

1. current reasoning effort
2. immediate-apply note
3. copyable commands:
   - `/reasoning low`
   - `/reasoning medium`
   - `/reasoning high`
   - `/reasoning xhigh`

### Tests

Add a test that verifies:

- current reasoning value is rendered
- `/reasoning xhigh` appears in text
- select widget still exists

### Acceptance

- users can switch reasoning without guessing the required command syntax

## Task 6: Improve `/home` Card

### Goal

Turn `/home` into the main operational card for Harness users.

### Files

- Modify: `core/engine.go`
- Modify: `core/i18n.go`
- Modify: `core/engine_test.go`

### Work

Update `renderHomeCard()` to:

1. honor the new Harness card config block
2. show a short interaction hint when copyable commands are enabled
3. include a compact fallback command section, prioritizing:
   - `/workspace`
   - `/provider`
   - `/provider switch codex_primary`
   - `/ai status`
   - `/ai tail`
   - `/ai resume`
   - `/ai stop`
4. preserve current recommended action buttons

### Tests

Expand the existing `/home` card test to verify:

- fallback commands are rendered
- configured title is used when set
- recommended buttons still exist

### Acceptance

- `/home` works as the first screen a mobile user can rely on

## Task 7: Add Feishu-Specific Interaction Copy

### Goal

Reduce user confusion around “selection already submits”.

### Files

- Modify: `core/i18n.go`
- Modify: `platform/feishu/platform_test.go` only if platform-specific behavior needs validation

### Work

Add localized strings for:

- immediate-apply hint
- callback failure fallback hint
- copyable command section label

Suggested Chinese copy:

- `选择后立即生效；如无反应，请复制下方命令`
- `可复制命令`

### Acceptance

- the card wording makes the UX self-explanatory

## Task 8: Regression Tests

### Files

- Modify: `core/engine_test.go`

### Minimum Coverage

Add tests for:

1. provider card renders fallback commands
2. model card renders fallback commands
3. reasoning card renders fallback commands
4. `/home` renders fallback commands
5. existing card action values remain present:
   - `nav:/help auto`
   - `act:/provider ...`
   - `act:/model ...`
   - `act:/reasoning ...`

### Acceptance

- card UX improvements do not break existing in-place navigation

## Out of Scope for Phase 1

The following are deferred:

- quota-triggered provider auto failover
- provider cooldown state
- model fallback chain / preferred model policy
- automatic selection of `gpt-5.4` when missing from the provider list

## Phase 2 Preview

Once Phase 1 is complete, the next phase should implement:

1. quota/rate-limit detection from Codex interactive errors
2. provider cooldown runtime state
3. automatic provider failover with user-facing notification
4. manual override compatibility with cooldown state
