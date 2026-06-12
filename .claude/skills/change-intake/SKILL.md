# Change Intake

Use `/change-intake` after WF8/WF9 or on a mature codebase when a new request
arrives. Classify before editing.

Routes:
- `bugfix` -> `/code-debug`
- `experiment_delta` -> `/iterate`
- `stable_code_delta` -> build delta plus `/code-debug`
- `architecture_delta` -> delta grill plus `/refine-arch` or `/build-plan`
- `evaluation_delta` -> Review Packet and contract gate
- `claim_boundary_delta` -> Claim Boundary review
- `new_research_direction` -> new Research Intent Draft branch
- `harness_guardrail_delta` -> `/harness-maintenance`
- `unknown` -> `STEER`

Supervisor CLI:

```bash
tooling/workflow_supervisor/scripts/workflow_ctl.sh start --segment change --goal "<request>" --json
tooling/workflow_supervisor/scripts/workflow_ctl.sh validate-postconditions --node-id change_classify_request --run-id <run_id> --json
```

The CLI writes the machine-readable Change Request under
`.workflow_supervisor/runs/<run_id>/runtime/change_request.json`. It only
classifies and routes; it does not invoke `/code-debug`, `/iterate`, Review
Packet tooling, delta grill, or `/harness-maintenance` by itself.

Fail closed on low confidence, contract impact, claim impact, primary metric
changes, public interface changes, or Harness guardrail changes. Produce a
Change Request matching `schemas/change_request.schema.json`, or pause with one
concrete steering question and Gate Evidence.
