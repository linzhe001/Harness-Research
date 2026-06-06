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
summary: "How Grill and execution supervisor form the two user-facing top-level modes without replacing Gate Evidence or Human Approval."
nav:
  section: "operate"
  position: 10
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
model. Operators choose one of two human-facing top-level modes first. Existing Skill-owned
artifact producers remain the internal execution map. Evidence tooling still
owns Evidence Chains and Review Packets. Human Approval is still required for
contracts, claim boundaries, high-risk transitions, and release decisions.

## Model

```text
Intent
  -> Grill or Execution Supervisor
  -> Supervisor action, when applicable
  -> Gate Evidence or typed HITL interrupt
  -> Next safe action
```

Top-level modes define the operator surface:

| Top-level mode | 什么时候用 | 主要状态面 |
| --- | --- | --- |
| `grill` | research intent 还不清楚 | Research Intent Draft 和 readiness candidates |
| `execution supervisor` | intent 已经能进入执行、验证、迭代、release，或成熟代码库出现新请求 | pending request、worker result JSON、Gate ledger、controller status |

Execution Supervisor actions are scoped commands under the second mode:

| Supervisor action | 什么时候用 | 主要状态面 |
| --- | --- | --- |
| `prepare` | intent 已存在，需要检查 readiness，或用 `--complete` 获取/验证数据集和 baseline | Dataset Stats、Baseline Report、Review Packet 和 pending request JSON |
| `build` | 需要推进 bounded implementation 并验证到可运行 | worker result JSON、Gate ledger、Validate Run Report 和 postcondition validation |
| `iterate` | 需要把 WF10 委托给 auto-iterate | `auto_iterate_ctl.sh status --json` 和 `iteration_log.json` |
| `release` | validate / package / submit action 需要 claim / approval check | WF12 Review Packet 和 scoped approval request |
| `change` | 成熟代码库收到新请求 | Change Request JSON 和 route confidence |

Detailed reference pages are still available, but they are not the first
question the operator answers. Open them only when you need internal artifact
ownership, postcondition details, or a Skill Contract field.

The v0 CLI is intentionally lightweight:

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

Default non-dry-run `prepare` is still the low-risk HITL PoC. It verifies
candidate readiness inputs, compiles a draft protocol packet under
`.evidence/protocol_compiler/**`, generates a WF5 Review Packet with
dynamic-context tooling, writes a pending request under
`.workflow_supervisor/**`, and waits for approve/revise/reject. Approval resume
reruns the WF5 dynamic-context gate and records `prepare_hitl_poc`, not
`prepare_complete`.

`prepare --complete` is the full prepare path. It verifies or acquires the
dataset, clones/copies/adopts the baseline, writes `docs/Dataset_Stats.md`,
`docs/Baseline_Report.md`, `docs/30_evidence/Dataset_Table.md`,
`docs/30_evidence/Baseline_Table.md`, updates `PROJECT_STATE.json` and
`project_map.json`, then runs protocol and Review Packet gates. Local sources
can be copied directly. On start it writes
`.workflow_supervisor/runs/<run_id>/runtime/grill_bridge.json` by reading
`.workflow_supervisor/readiness.json`, `docs/Execution_Readiness_Packet.md`,
`docs/Research_Intent_Draft.md`, and `docs/Grill_Round_Log.md`. It uses only
structured readiness rows, explicit `key: value` lines, or labeled contextual
dataset/baseline URLs. Dataset downloads and remote baseline clones require
`--allow-external-downloads` or an explicit Grill readiness policy such as
`external_download_policy: allow`. Redacted or ambiguous values become typed
input requests. The segment still pauses for Human Approval before recording
`prepare_complete`.

`build` runs registry nodes in order through deterministic checks or structured
workers. `--auto` delegates non-deterministic nodes to Codex with full-auto
sandboxing. `--worker-command` supplies a testable command template that must
write a schema-valid worker result JSON. The segment records
`build_ready_for_iterate` only after the validate-run node and its
postconditions pass. Missing inputs, worker failures, invalid Gate ledgers, or
failed postconditions stop the run with a typed request or failure record.
Worker prompts include node postconditions and allowed write patterns; workers
must run concrete checks and record PASS/FAIL/NOT_RUN Gate ledger entries before
claiming success. Codex workers write result JSON to
`.agents/state/workflow_supervisor_worker_results/**`; the supervisor validates
and adopts it into `.workflow_supervisor/**`.

Registry coverage includes data-prep, baseline-repro, refine-arch, build-plan,
code-expert/code-debug, and validate-run. Postcondition validation records
PASS/FAIL/NOT_RUN from artifacts, schema checks, forbidden-write checks, and
worker Gate ledger.

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

`prepare_complete` is the prepare state that later execution can depend on. It
requires data and baseline artifacts plus the required approval/revision gate.

`build_ready_for_iterate` means build has reached validate-run and the
configured runnable postconditions passed. It does not start WF10 by itself.

`approve` on the supervisor CLI is scoped to a pending request and must preserve
`approval_source`. It is not a local boolean toggle.

## Related Pages

- [[page:operator_task_index|Operator Action Index]]
- [[skill:grill]]
- [[skill:workflow-supervisor]]
- [[skill:change-intake]]
- [[page:evidence_approval_model|Evidence And Approval]]
- [[page:auto_iterate_model|Auto-Iterate]]
