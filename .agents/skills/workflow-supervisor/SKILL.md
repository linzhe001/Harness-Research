---
name: workflow-supervisor
description: "Internal Harness instruction source for workflow-supervisor. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Workflow Supervisor

Use this Skill for `harness prepare`, `build`, `iterate`, `release`, `change`,
or direct `workflow_ctl` work. It orchestrates Skills but does not replace Stage
Skills, Evidence Chain tooling, Gate Evidence, or Human Approval.

## Read First

- `../../../AGENTS.md`, `../../../CLAUDE.md`
- `../../../.agents/references/workflow-supervisor-runtime.md`
- `../../../tooling/workflow_supervisor/config/default_nodes.json`
- `../../../tooling/workflow_supervisor/config/gate_policy.yaml`
- `../../../.agents/references/commit-checkpoint-rule.md`
- Workflow, context, contract, evidence, language, and ubiquitous-language rules
  under `../../../.agents/references/`

## Runtime Boundary

`.workflow_supervisor/**` is supervisor-owned. Do not edit it manually. Use
`tooling/workflow_supervisor/scripts/workflow_ctl.sh` or `harness.sh`.
The supervisor may read `.auto_iterate/**` status but must not write it.
For stuck workers, follow `Worker Process Safety` in the runtime reference: use `status` / `recover` / `tail` / `stop`; do not `kill` Codex worker PIDs from the active session/process group unless isolation is verified.

Common commands:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json  # or worker-status --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>" --dry-run
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --complete --goal-file docs/05_intake/Research_Intent_Draft.md --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --complete --dataset-source <path-or-url> --dataset-target <path> --baseline-repo <path-or-url> --allow-external-downloads
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment build --goal "<goal>" --auto
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment iterate --goal "<goal>" --auto-goal docs/auto_iterate_goal.md
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment change --goal "<new request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment release --goal "validate release" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-postconditions --node-id <node> --run-id <run_id> --worker-result <result.json> --json
```

## Bare Post-Grill Start

When the operator invokes bare `$workflow-supervisor` after an accepted Grill
draft, do not ask them to hand-build CLI arguments.

1. Run `status --json` and report active pending-request fields: `question`,
   `allowed_responses`, `reason`, `node_id`, `gate_status_refs`,
   `request_snapshot_hash`, `blocked_by`, `resume_command`, and `recovery`.
2. If a run/request is active, run `recover --repair-stale-running --auto-resume-answered --json`; if it recommends `resume_answered_pending_request`, resume, otherwise report the input/manual/approval blocker and stop.
3. If no run is active and Grill docs exist, start:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh start \
  --segment prepare \
  --complete \
  --goal-file docs/05_intake/Research_Intent_Draft.md \
  --json
```

Full prepare reads the Grill bridge. Missing/redacted/ambiguous datasets or
baselines become typed pending requests. Do not silently add
`--allow-external-downloads`.

## Segment Rules

- `prepare --complete`: readiness preflight, acquisition plan schema check,
  deterministic dataset verification/acquisition, baseline clone/acquisition,
  manifest schema checks, protocol compiler, WF5 review packet, then
  `prepare_complete` when gates pass. It preserves candidate/rejected/deferred/
  requires-approval distinctions from the Grill bridge.
- `build`: normal path `build_refine_arch -> build_plan -> build_code_expert ->
  build_validate_run`; `build_code_debug` is failure recovery. Build reaches
  `build_ready_for_iterate` only after validate-run gates pass. Durable outputs
  need commit checkpoints; WF8 needs one per roadmap `commit_plan` row. Routine
  loops run action-local checks; heavy checks run at checkpoint profiles.
- `iterate`: delegates to `auto_iterate_ctl.py`; `monitor-iterate` maps
  `status --json`, manual action, or pause into supervisor state.
- `change`: deterministic Change Intake; writes a Change Request JSON and
  routes or pauses, but does not edit code/contracts by itself.
- `release`: conservative WF11 final experiment matrix plus WF12 gate for
  explicit `validate`, `package`, or `submit` intent; approval resume records
  approval only.

## Worker Contract

Workers return schema-validated JSON, not prose decisions. Codex worker result
handoff lives under `.agents/state/workflow_supervisor_worker_results/**`; the
supervisor validates and adopts it into `.workflow_supervisor/**`.
Workers must report live semantic progress with `worker-event`; never hand-write
`.workflow_supervisor/**`. `status --json` and `worker-status --json` expose
`active_worker.telemetry_state` for stuck-worker recovery.

For every `command_passes` postcondition, worker results need an exactly
matching Gate ledger `command`. Build uses `roadmap implementation completeness`
for code nodes and `validate-run verdict` for WF9; missing runnable evidence is
FAIL, REVIEW, or NOT_RUN, not PASS. Build postconditions verify
`git_worktree_clean`; code nodes also verify `sliced_commits_recorded` from the
run `base_git_commit`.

Worker prompts are budgeted by segment: compact postconditions, evidence
tools, allowed write patterns, truncated goal context, and explicit
`node_retry_limit` / `gate_cycle_limit`. Workers read referenced artifacts
directly when more context is needed and record those reads in the Gate ledger.
Supervisor runs record their active risk profile from
`tooling/workflow_supervisor/config/gate_policy.yaml`.

Missing handoff JSON may be synthesized only when concrete artifact/schema
postconditions pass and no required command or git commit gate is missing.

## Hook Boundary

Harness hooks should warn for missing context and block only narrow
tool-owned/generated paths: `.evidence/**`, `.auto_iterate/**`,
`.workflow_supervisor/**`, `docs/_views/**`, and `docs/_site/**`. Ordinary
declared implementation writes under `src/`, `scripts/`, `configs/`,
`project_map.json`, and owned docs are not hard-blocked by hooks.

## HITL And Exit

Typed pending requests live in `.workflow_supervisor/pending_request.json`.
Review Packets are decision inputs, not Approval Evidence. `approve_contract.py`
may run only after explicit Human Approval.

Report segment, run id, state status, pending request if any, Gate ledger,
unresolved assumptions, and next safe action.
