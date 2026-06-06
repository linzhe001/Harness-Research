---
name: workflow-supervisor
description: "Operate the Harness execution supervisor CLI and runtime boundaries. Use for harness prepare/build/iterate/release/change dry runs, status, pause, resume, typed HITL requests, and worker-result validation."
---

# Workflow Supervisor

## Purpose

Use this Skill when the operator asks for `harness prepare`, `harness build`,
`harness iterate`, `harness release`, `harness change`, or direct
`workflow_ctl` work. The supervisor is an orchestration layer over existing
Skills; it does not replace Stage Skills, Evidence Chain tooling, or Human
Approval.

## References

Read these first:
- `../../../AGENTS.md`
- `../../../CLAUDE.md`
- `../../../docs/grill_execution_supervisor.md`
- `../../../docs/grill_execution_supervisor_implementation_plan.md`
- `../../../tooling/workflow_supervisor/config/default_nodes.json`
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/evidence-chain-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/ubiquitous-language.md`

## Runtime Ownership

The supervisor owns `.workflow_supervisor/**`. Do not edit that directory
manually. Use:

```bash
tooling/workflow_supervisor/scripts/harness.sh prepare --goal "<goal>" --dry-run
tooling/workflow_supervisor/scripts/harness.sh change --goal "<new request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>" --dry-run
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>"
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>" --complete --dataset-source <path-or-url> --dataset-target <path> --baseline-repo <path-or-url> --allow-external-downloads
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment build --goal "<goal>" --auto
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment build --goal "<goal>" --worker-command '<command template>'
tooling/workflow_supervisor/scripts/workflow_ctl.sh approve --request-id <id> --decision approve --approved-by "<human>" --approval-source ".evidence/review_packets/<stage>/<build_id>/review_packet.md"
tooling/workflow_supervisor/scripts/workflow_ctl.sh resume --request-id <id>
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-postconditions --node-id build_validate_run --run-id <run_id> --worker-result <result.json> --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment iterate --goal "<goal>" --auto-goal docs/auto_iterate_goal.md
tooling/workflow_supervisor/scripts/workflow_ctl.sh monitor-iterate --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment change --goal "<new request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment release --goal "package release artifacts" --json
```

Non-dry-run `prepare` is a HITL PoC in v0: it verifies candidate readiness
inputs, compiles a draft protocol packet through evidence tooling, runs the WF5
dynamic-context review-packet tooling, creates an `APPROVE_ACTION` pending
request, and resumes to `prepare_hitl_poc`, `prepare_revision_requested`, or
`prepare_rejected`.
For approve decisions on contract approval requests, `workflow_ctl approve`
runs the exact `approve_contract.py` action with the recorded
`approval_source`; revise/reject never mark a contract approved.
`prepare_hitl_poc` must not unlock build, iterate, or release.

Slice 5 registry coverage includes data-prep, baseline-repro,
refine-arch/build-plan/code-expert/code-debug, and validate-run nodes.
`start --segment prepare --complete` runs readiness preflight, deterministic
dataset acquisition or verification, baseline clone/acquisition, protocol
compiler, and WF5 review-packet generation. External dataset downloads or
baseline clones require either `--allow-external-downloads` or an explicit
`external_download_policy` / `allow_external_downloads` readiness value captured
by Grill. Local paths can be copied or verified without that flag. When
`--complete` starts, the supervisor writes
`.workflow_supervisor/runs/<run_id>/runtime/grill_bridge.json` by reading
`.workflow_supervisor/readiness.json`, `docs/Execution_Readiness_Packet.md`,
`docs/Research_Intent_Draft.md`, and `docs/Grill_Round_Log.md`. It uses only
structured readiness rows, explicit `key: value` lines, or labeled contextual
dataset/baseline URLs; redacted or ambiguous values become typed input
requests. A successful full prepare still pauses for the WF5 approval request
and resumes to `prepare_complete` only after explicit approval.
`start --segment build` now runs the build node registry through structured
workers. Use `--auto` to delegate non-deterministic nodes to Codex, or
`--worker-command` to provide a command template that writes
`schemas/workflow_supervisor_worker_result.schema.json`. Build completes only
as `build_ready_for_iterate` after the validate-run node and its postconditions
pass. Worker prompts include the node postconditions and allowed write patterns;
workers must run concrete checks, debug failures inside the node budget, and
record PASS/FAIL/NOT_RUN in Gate ledger instead of relying on prose.
`validate-postconditions` records PASS/FAIL/NOT_RUN from artifacts, worker
writes, schemas, and worker Gate ledger.
Codex workers write their JSON result to a temporary
`.agents/state/workflow_supervisor_worker_results/**` handoff path; the
supervisor validates and adopts that result into `.workflow_supervisor/**`.

Harness hooks do not block ordinary build writes to declared implementation
surfaces such as `src/`, `scripts/`, `configs/`, `project_map.json`, and owned
docs. They do block manual writes to tool-owned runtime/generated paths such as
`.evidence/**`, `.auto_iterate/**`, `.workflow_supervisor/**`, `docs/_views/**`,
and `docs/_site/**`; supervisor/evidence/docs-site tooling may still write
those paths through the owning commands.

The supervisor may read `.auto_iterate/**` status but must not write it.
WF10 runtime remains owned by `tooling/auto_iterate/**`.
`start --segment iterate` delegates to `auto_iterate_ctl.py`; `monitor-iterate`
bridges `status --json` and maps `manual_action_required` or operator pause to
a supervisor `STEER` request.

`start --segment change` runs deterministic Change Intake. It writes a
schema-validated Change Request under
`.workflow_supervisor/runs/<run_id>/runtime/change_request.json`, routes
high-confidence deltas to the selected Skill entrypoint, and pauses with a
typed `STEER` request when confidence is low. It does not invoke the routed
Skill or edit code/contracts by itself.

`start --segment release` is a conservative WF12 approval gate. It requires an
explicit `validate`, `package`, or `submit` action in the goal, runs the WF12
dynamic-context Review Packet gate, and pauses with `APPROVE_ACTION` only after
the gate passes with dynamic context plus approved Project Contract,
Evaluation Contract, and Claim Boundary. Approval resume reruns the WF12 gate
and records the approval payload only; it does not package or submit.

## Worker Contract

Supervisor decisions must come from structured worker result JSON validated by
`schemas/workflow_supervisor_worker_result.schema.json`, not from worker prose.
Workers must not ask the user directly, approve contracts, or write supervisor
runtime state.

## HITL Rules

Typed pending requests live in `.workflow_supervisor/pending_request.json`.
Approval requests must preserve `approval_source`. Review Packets are decision
inputs, not Approval Evidence. `approve_contract.py` may run only after
explicit Human Approval.

## Exit Condition

Report:
- segment and run id,
- state status,
- pending request if any,
- Gate ledger for commands run or `NOT_RUN` with reason,
- unresolved assumptions and next safe action.
