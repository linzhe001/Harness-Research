---
name: workflow-supervisor
description: "Operate the Harness execution supervisor CLI and runtime boundaries for prepare/build/iterate/release/change segments, typed HITL, and worker-result validation."
argument-hint: "[status|start|pause|resume|approve|validate]"
allowed-tools: Read, Bash, Glob, Grep
---

# Workflow Supervisor

Use `/workflow-supervisor` for `harness prepare`, `harness build`,
`harness iterate`, `harness release`, `harness change`, and direct
`workflow_ctl` work. The supervisor owns `.workflow_supervisor/**` and must be
operated through tooling, not manual edits.

Core commands:

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

Non-dry-run `prepare` is a v0 HITL PoC. It verifies candidate readiness inputs,
compiles a draft protocol packet through evidence tooling, generates a WF5
Review Packet, and pauses as an `APPROVE_ACTION`; resume records
`prepare_hitl_poc`, `prepare_revision_requested`, or `prepare_rejected`.
For approve decisions on contract approval requests, `workflow_ctl approve`
runs the exact `approve_contract.py` action with the recorded
`approval_source`; revise/reject never mark a contract approved.
`prepare_hitl_poc` is not `prepare_complete` and must not unlock later segments.

The registry now covers Slice 5 Data/Baseline/Build nodes. Postcondition
validation records PASS/FAIL/NOT_RUN from artifacts, schemas, worker writes,
and worker Gate ledger.
`start --segment prepare --complete` runs readiness preflight, deterministic
dataset acquisition or verification, baseline clone/acquisition, protocol
compiler, and WF5 Review Packet generation. External dataset downloads or
baseline clones require either `--allow-external-downloads` or an explicit
`external_download_policy` / `allow_external_downloads` readiness value captured
by Grill. When `--complete` starts, the supervisor writes
`.workflow_supervisor/runs/<run_id>/runtime/grill_bridge.json` by reading
`.workflow_supervisor/readiness.json`, `docs/Execution_Readiness_Packet.md`,
`docs/Research_Intent_Draft.md`, and `docs/Grill_Round_Log.md`. It uses only
structured readiness rows, explicit `key: value` lines, or labeled contextual
dataset/baseline URLs; redacted or ambiguous values become typed input
requests. Successful full prepare still pauses for explicit approval and
resumes to `prepare_complete` only after approval.
`start --segment build` runs the build registry through structured workers.
Use `--auto` for Codex delegation, or `--worker-command` for a command template
that writes `schemas/workflow_supervisor_worker_result.schema.json`. Build
completes only as `build_ready_for_iterate` after validate-run postconditions
pass. Worker prompts include the node postconditions and allowed write patterns;
workers must run concrete checks, debug failures inside the node budget, and
record PASS/FAIL/NOT_RUN in Gate ledger instead of relying on prose.
Codex workers write their JSON result to a temporary
`.agents/state/workflow_supervisor_worker_results/**` handoff path; the
supervisor validates and adopts that result into `.workflow_supervisor/**`.

Harness hooks do not block ordinary build writes to declared implementation
surfaces such as `src/`, `scripts/`, `configs/`, `project_map.json`, and owned
docs. They do block manual writes to tool-owned runtime/generated paths such as
`.evidence/**`, `.auto_iterate/**`, `.workflow_supervisor/**`, `docs/_views/**`,
and `docs/_site/**`; supervisor/evidence/docs-site tooling may still write
those paths through the owning commands.

Do not treat Review Packets as Approval Evidence. Preserve `approval_source`
for approval resumes. The supervisor may read `.auto_iterate/**` but does not
write it. `start --segment iterate` delegates to `auto_iterate_ctl.py`, and
`monitor-iterate` maps `manual_action_required` or operator pause to a
supervisor `STEER` request.

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

Exit by reporting run id, segment status, pending request, Gate ledger, and the
next safe action.
