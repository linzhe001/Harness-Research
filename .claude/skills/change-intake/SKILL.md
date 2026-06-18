# Change Intake

Use `/change-intake` after WF8/WF9 or on a mature codebase when a new request
arrives. Classify before editing.

Read `.claude/shared/research-supervision-patterns.md` and
`.claude/shared/research-supervision/idea-evaluation.md` when the request
changes the research direction, claim boundary, evaluation target, dominant
improvement axis, or feasibility story. These assets pressure-test the route;
they do not approve the change.

Routes:
- `bugfix` -> `/code-debug`
- `experiment_delta` -> `/iterate`
- `stable_code_delta` -> build delta plus `/code-debug`
- `architecture_delta` -> delta grill plus `/refine-arch` or `/build-plan`
- `evaluation_delta` -> evaluation delta route plus Gate ledger and
  `pre_eval_commit` requirement before metric-bearing eval
- `claim_boundary_delta` -> Claim Delta Evidence plus owning claim/release or
  writing route
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

Fail closed on low confidence, public interface changes, or Harness guardrail
changes. Evaluation, Baseline, or Claim Boundary impact routes to the owning
workflow with a Gate ledger, Claim Delta Evidence when claims change, and a
commit checkpoint requirement before train/eval. It does not pause for approval
when the change stays inside the active Automation Policy. Produce a Change
Request matching `schemas/change_request.schema.json`, or pause with one
concrete steering question and Gate Evidence.
