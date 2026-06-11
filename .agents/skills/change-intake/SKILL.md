---
name: change-intake
description: "Classify post-codebase requests into bugfix, experiment delta, stable code delta, architecture delta, evaluation delta, claim-boundary delta, new research direction, harness guardrail delta, or steer."
---

# Change Intake

## Purpose

Use Change Intake after a codebase exists or after WF8/WF9 when the operator
brings a new request, idea, config change, or code delta. The goal is to route
the change without silently rerunning WF1-WF12 or making broad edits.

## References

Read these first:
- `../../../AGENTS.md`
- `../../../CLAUDE.md`
- `../../../.agents/references/workflow-supervisor-runtime.md`
- `../../../.agents/references/workflow-guide.md`
- `../../../.agents/references/context-layering-policy.md`
- `../../../.agents/references/contract-gating-rule.md`
- `../../../.agents/references/evidence-chain-rule.md`
- `../../../.agents/references/project-map-rule.md`
- `../../../.agents/references/language-policy.md`
- `../../../.agents/references/ubiquitous-language.md`

## Classifier Inputs

Read current context when present:
- `PROJECT_STATE.json`
- `project_map.json`
- `docs/20_facts/Codebase_Map.md`
- `docs/10_contract/Project_Contract.md`
- `docs/10_contract/Evaluation_Contract.md`
- `docs/10_contract/Baseline_Contract.md`
- `docs/10_contract/Claim_Boundary.md`
- latest relevant `iteration_log.json` entry

## Routes

- `bugfix` -> `$code-debug`
- `experiment_delta` -> `$iterate`
- `stable_code_delta` -> build delta plus `$code-debug`
- `architecture_delta` -> delta grill, `$refine-arch`, `$build-plan`
- `evaluation_delta` -> Review Packet and contract gate
- `claim_boundary_delta` -> Claim Boundary review
- `new_research_direction` -> new Research Intent Draft branch
- `harness_guardrail_delta` -> `$harness-maintenance`
- `unknown` -> `STEER`

## Supervisor CLI

Use the supervisor entrypoint when the operator wants a recorded route:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment change --goal "<request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-postconditions --node-id change_classify_request --run-id <run_id> --json
```

The CLI writes the machine-readable Change Request under
`.workflow_supervisor/runs/<run_id>/runtime/change_request.json`. It only
classifies and routes; it does not invoke `$code-debug`, `$iterate`, Review
Packet tooling, delta grill, or `$harness-maintenance` by itself.

## Fail-Closed Rules

- `confidence=low` routes to `STEER`, not code edits.
- Evaluation, Baseline, or Claim Boundary impact routes to review/approval.
- Public interface, config schema, data flow, or primary metric changes are not
  plain bugfixes.
- Harness guardrail changes never route to `$code-debug`.

## Exit Condition

Produce a Change Request matching `schemas/change_request.schema.json`, or
pause with one concrete steering question and a Gate ledger.
