---
schema_version: "0.1"
page_id: "workflow_supervisor_model"
title: "Workflow Supervisor Model"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/workflow_supervisor_model.md"
source_of_truth: true
status: "current"
summary: "How Grill, execution supervisor, and change intake sit above existing Stage Skills without replacing Gate Evidence or Human Approval."
nav:
  section: "details"
  position: 46
canonical_sources:
  - path: "docs/grill_execution_supervisor.md"
    role: "aggregate_source"
  - path: "docs/grill_execution_supervisor_implementation_plan.md"
    role: "aggregate_source"
  - path: "tooling/workflow_supervisor/config/default_nodes.json"
    role: "tooling"
references: ["skill:grill", "skill:workflow-supervisor", "skill:change-intake", "term:Gate Evidence", "term:Human Approval"]
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/workflow_supervisor_model.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Workflow Supervisor Model

## Purpose

The supervisor layer reduces workflow friction without changing the authority
model. Existing Stage Skills still produce Stage artifacts. Evidence tooling
still owns Evidence Chains and Review Packets. Human Approval is still required
for contracts, claim boundaries, high-risk transitions, and release decisions.

## Model

```text
Intent
  -> Entrypoint
  -> Stage
  -> Skill
  -> Gate
```

Entrypoints add routing semantics:

- `grill`: draft-only WF1-WF3 intent clarification.
- `prepare`, `build`, `iterate`, `release`: supervised execution segments.
- `change`: mature-codebase delta classification.

The v0 CLI is intentionally lightweight:

```bash
tooling/workflow_supervisor/scripts/harness.sh prepare --goal "<goal>" --dry-run
tooling/workflow_supervisor/scripts/harness.sh change --goal "<new request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh status --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>" --dry-run
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment prepare --goal "<goal>"
tooling/workflow_supervisor/scripts/workflow_ctl.sh approve --request-id <id> --decision approve --approved-by "<human>" --approval-source ".evidence/review_packets/<stage>/<build_id>/review_packet.md"
tooling/workflow_supervisor/scripts/workflow_ctl.sh resume --request-id <id>
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-nodes
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-postconditions --node-id build_validate_run --run-id <run_id> --worker-result <result.json> --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment iterate --goal "<goal>" --auto-goal docs/auto_iterate_goal.md
tooling/workflow_supervisor/scripts/workflow_ctl.sh monitor-iterate --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment change --goal "<new request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment release --goal "package release artifacts" --json
```

Non-dry-run `prepare` is a v0 HITL PoC. It verifies candidate readiness inputs,
compiles a draft protocol packet under `.evidence/protocol_compiler/**`, then
generates a WF5 Review Packet with dynamic-context tooling. It writes the
pending request under `.workflow_supervisor/**` and waits for
approve/revise/reject. For an explicit approve decision on a contract approval
request, `workflow_ctl approve` runs the exact `approve_contract.py` action
with the recorded `approval_source`; revise/reject never mark a contract
approved. Approval resume reruns the WF5 dynamic-context gate and records
`prepare_hitl_poc`, not `prepare_complete`.

Slice 5 adds registry coverage for data-prep, baseline-repro, refine-arch,
build-plan, code-expert/code-debug, and validate-run. Postcondition validation
records PASS/FAIL/NOT_RUN from artifacts, schema checks, forbidden-write
checks, and worker Gate ledger. It does not execute Stage Skills by itself.

Slice 6 delegates WF10 to the existing auto-iterate controller. The supervisor
launches `auto_iterate_ctl.py`, records status snapshots under
`.workflow_supervisor/**`, reads `.auto_iterate/state.json` through
`status --json`, and maps `manual_action_required` or operator pause to a
typed `STEER` request. It must not write `.auto_iterate/**` directly.

Slice 7 adds deterministic Change Intake. The supervisor reads the operator
request plus available context hints, writes a schema-validated Change Request
under `.workflow_supervisor/runs/<run_id>/runtime/change_request.json`, and
records a route such as `code-debug`, `iterate`, `build_delta`,
`review_packet`, `claim_boundary_review`, `delta_grill`, or
`harness-maintenance`. Low-confidence requests fail closed into a typed
`STEER` request. The supervisor records the route only; it does not invoke the
routed Skill or edit code/contracts by itself.

Slice 8 adds the conservative Release Segment gate. The registry contains WF11
`final-exp` and WF12 `release` nodes. Non-dry-run `release` requires an
explicit `validate`, `package`, or `submit` action, runs
`check_dynamic_context.py --stage wf12 --review-packet`, and pauses with an
exact scoped `APPROVE_ACTION` only when dynamic context is active and Project
Contract, Evaluation Contract, and Claim Boundary approvals are confirmed. If
the WF12 gate fails, approvals are missing, or the action is unclear, the
supervisor creates a typed `STEER` request. Resume records the approval payload
and reruns WF12 gates; it does not package or submit.

## Boundaries

- `.workflow_supervisor/**` is supervisor-owned runtime state. Inspect it for
  recovery, but do not edit it by hand.
- `.auto_iterate/**` remains owned by the WF10 auto-iterate controller.
- `.evidence/**` remains owned by evidence tooling.
- Worker results must be structured JSON, not prose-only completion claims.
- Review Packets are decision inputs, not Approval Evidence.

## Common Confusions

`grill_draft_ready` does not mean WF1-WF3 are complete. It means draft intent
artifacts exist and can be used as context for canonical Stage Skills.

`prepare_hitl_poc` does not unlock build, iterate, or release. It proves
readiness/HITL plumbing only.

`approve` on the supervisor CLI is scoped to a pending request and must preserve
`approval_source`. It is not a local boolean toggle.

## Related Pages

- [[skill:grill]]
- [[skill:workflow-supervisor]]
- [[skill:change-intake]]
- [[page:evidence_approval_model|Evidence And Approval]]
- [[page:auto_iterate_model|Auto-Iterate]]
