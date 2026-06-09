---
name: workflow-supervisor
description: "Operate the Harness execution supervisor CLI and runtime boundaries. Use for harness prepare/build/iterate/release/change dry runs, status, pause, resume, typed HITL requests, and worker-result validation."
---

# Workflow Supervisor

Use this Skill for `harness prepare`, `build`, `iterate`, `release`, `change`,
or direct `workflow_ctl` work. The supervisor orchestrates existing Skills; it
does not replace Stage Skills, Evidence Chain tooling, Gate Evidence, or Human
Approval.

## Read First

- `../../../AGENTS.md`, `../../../CLAUDE.md`
- `../../../docs/grill_execution_supervisor.md`
- `../../../docs/grill_execution_supervisor_implementation_plan.md`
- `../../../tooling/workflow_supervisor/config/default_nodes.json`
- Workflow, context, contract, evidence, language, and ubiquitous-language
  rules under `../../../.agents/references/`

## Runtime Boundary

`.workflow_supervisor/**` is supervisor-owned. Do not edit it manually. Use
`tooling/workflow_supervisor/scripts/workflow_ctl.sh` or `harness.sh`.
The supervisor may read `.auto_iterate/**` status but must not write it.

Common commands:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>" --dry-run
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --complete --goal-file docs/Research_Intent_Draft.md --json
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

1. Run `status --json` and report any active typed pending requests, including
   `question`, `allowed_responses`, `reason`, `node_id`, `gate_status_refs`,
   `request_snapshot_hash`, `blocked_by`, `resume_command`, and `recovery`.
2. If a run or pending request is active, run:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh recover \
  --repair-stale-running \
  --auto-resume-answered \
  --json
```

The shorthand command shape is
`recover --repair-stale-running --auto-resume-answered --json`. If the payload
recommends `resume_answered_pending_request`, run `resume --request-id <id>
--json`. If it requires `answer_pending_request`, `manual_recover`, or an
approval without Approval Evidence, report the request and stop.
3. If no run is active and Grill docs exist, start:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh start \
  --segment prepare \
  --complete \
  --goal-file docs/Research_Intent_Draft.md \
  --json
```

Full prepare reads the Grill bridge. Missing/redacted/ambiguous datasets or
baselines become typed pending requests. Do not silently add
`--allow-external-downloads`; external downloads/clones require that flag,
`external_download_policy`, `allow_external_downloads`, `hf_access_policy`, or
a narrower Grill source-specific policy.

## Segment Rules

- `prepare --complete`: readiness preflight, acquisition plan schema check,
  deterministic dataset verification/acquisition, baseline clone/acquisition,
  manifest schema checks, protocol compiler, WF5 review packet, then approval
  pause. It preserves candidate/rejected/deferred/
  requires-approval distinctions from the Grill bridge.
- `build`: structured node workers. Build becomes `build_ready_for_iterate`
  only after validate-run postconditions pass.
- `iterate`: delegates to `auto_iterate_ctl.py`; `monitor-iterate` maps
  `status --json`, manual action, or pause into supervisor state.
- `change`: deterministic Change Intake; writes a Change Request JSON and
  routes or pauses, but does not edit code/contracts by itself.
- `release`: conservative WF12 gate for explicit `validate`, `package`, or
  `submit` intent; approval resume records approval only.

## Worker Contract

Workers return schema-validated JSON, not prose decisions. Codex worker result
handoff lives under `.agents/state/workflow_supervisor_worker_results/**`; the
supervisor validates and adopts it into `.workflow_supervisor/**`.

Worker prompts are budgeted by segment: compact postconditions, allowed write
patterns, truncated goal context, and explicit `node_retry_limit` /
`gate_cycle_limit`. Workers read referenced artifacts directly when more
context is needed and record those reads in the Gate ledger.
Supervisor runs record their active risk profile from
`tooling/workflow_supervisor/config/gate_policy.yaml`.

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
