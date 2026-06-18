---
name: grill
description: "Clarify early research intent through hard questions and produce draft-only Research Intent, Grill Round Log, and Execution Readiness Packet artifacts. Does not approve contracts or complete WF1-WF3 by itself."
---

# Grill

Use Grill before execution automation when the idea, baseline set, dataset set,
claim boundary, or failure condition is not yet clear. Grill is
conversation-first and draft-only.

## Read First
- `../../../AGENTS.md`, `../../../CLAUDE.md`
- `../../../.agents/references/workflow-supervisor-runtime.md`
- `../../../.agents/skills/init-project/SKILL.md`
- workflow/context/documentation/language rules and research-supervision assets
  under `../../../.agents/references/`

## Conversation Contract
Start with one short restatement of the current intent, then ask 3-5 blocking
questions that would change the next safe action. Do not start with a finished
draft, approval, or long questionnaire.

Each round records:
- operator answer summary
- critique lens: skeptic, methodologist, implementation, or claim-boundary
- current gap check
- next blocking question or explicit exit choice
- exit recommendation and human exit decision status

The agent may recommend `continue_grill`, `grill_draft_ready`,
`bridge_wf1_wf3`, `pivot`, or `abandon`, but the operator owns the exit
decision.

## Readiness Target
Before recommending `grill_draft_ready`, make these candidate-clear or record
the blocker explicitly:
- concrete operator observation, candidate claim, falsifier, metric/signal
- problem type, dominant improvement axis, reviewer risk, and fatal-flaw status
- maximum claim boundary and forbidden claims
- pivot / abort condition
- dataset source, access status, and local/private target when known
- baseline or negative-control source, including a code repository URL or
  `baseline_repo_missing`
- model/teacher/detector weight source, access policy, and cache target
- compute, budget, registration, and approval assumptions that would stop
  `prepare`
- Automation Policy candidate: auto-proceed flows after Grill, budget, forbidden
  directions, external access, watchdog expectations, and narrow human-stop
  cases such as Grill exit, approval tools, or irreversible external submit

Datasets need a direct downloadable source/API/Hugging Face id/release URL or
exact private path. Baselines need a concrete repo, official entrypoint, or
exact private path. Model weights need a Hugging Face id, download/checkpoint
URL, or exact private path. Paper pages, method pages, project pages, method
names, and model families are non-executable until source, access policy, and
target are clear.

## Outputs
Grill may create or refresh:
- `docs/05_intake/Research_Intent_Draft.md`
- `docs/05_intake/Grill_Round_Log.md`
- `docs/05_intake/Execution_Readiness_Packet.md`
- `.workflow_supervisor/readiness.json` only through Grill/supervisor tooling

In `docs/05_intake/Execution_Readiness_Packet.md`, keep compact ledgers for:
Dataset Access, `Baseline Source Ledger`, model weights,
`Execution Intent Ledger`, and Automation Policy. Each row records id/name,
source/policy, probe/access verdict, execution decision, target/notes, and for
automation: auto-proceed verdict, limits, forbidden directions, evidence needs,
and human-stop condition.

Execution decisions are `candidate`, `rejected`, `requires_approval`, or
`deferred`. Active rows must not remain `pending`; use blockers such as
`baseline_repo_missing`, `missing_dataset_source`, `requires_approval`, or
`deferred`.

For policy rows, use readiness input `kind: policy` with stable keys including
`hf_access_policy`, `non_hf_registration_policy`, `baseline_clone_policy`,
`baseline_clone_scope`, model access/download policy/scope, and external
downloads. These are candidate inputs, not Approval Evidence or Approved
Contracts. Readiness JSON keeps
external policy, approved datasets/baselines, targets, unknowns,
`operator_approved_at`, and an `automation_policy` object after accepted Grill
handoff. Include
`auto_proceed_flows`, `manual_approval_flows`, `budget`, `forbidden_directions`,
`assurance_axes`, `watchdog_policy`, `claim_delta_policy`,
`commit_checkpoint_policy`, and `stop_conditions`.
Dataset rows may include `target`, `license`, and `max_size_gb`; baseline rows
may include `repo`, `ref`, and `target`. Weight targets belong in
`target_paths` keys such as `model_cache` or `model_<id>` until a native
`approved_weights` schema exists.

## Tooling
Prefer helpers for durable writes:
```bash
python tooling/grill/questions.py --lens intake
python tooling/grill/draft.py --workspace-root . init --seed "<idea>"
python tooling/grill/draft.py --workspace-root . round --lens skeptic --answer-summary "<summary>" --gap-check "<gap>" --next-question "<question>" --exit-recommendation continue_grill
python tooling/grill/draft.py --workspace-root . packet --readiness-json <path>
python tooling/grill/readiness.py --workspace-root . --check --verify-paths --json
python tooling/grill/readiness.py --workspace-root . --write-readiness --input-json <path> --json
```

Use `--write-readiness` only for intentional tooling-owned writes to
`.workflow_supervisor/readiness.json`.

## Boundaries
- Do not mark WF1-WF3 complete from Grill output alone.
- Do not create Approved Contracts or Approval Evidence.
- Do not write `.evidence/**` or `.workflow_supervisor/**` by hand.
- Do not create `PROJECT_STATE.json`, `project_map.json`, or
  `iteration_log.json`.
- Do not promote Grill draft facts into current docs without the owning Stage
  Skill, Evidence Chain tooling, or explicit bridge path.

## Handoff
When the operator confirms `grill_draft_ready` or asks to proceed from an
accepted draft, continue with the internal `init-project update-from-grill`
mode unless the operator asks to skip guidance initialization. Inputs are the
three Grill docs and `.workflow_supervisor/readiness.json` when supervisor
tooling produced it.

The handoff initializes or refreshes `CLAUDE.md`, `AGENTS.md`, and `README.md`
from candidate Grill context only, preserves `## Custom`, keeps dataset and
baseline items candidate until `prepare` / WF4-WF5 verify them, and must not
mark WF1-WF3 complete. If not run, report
`init_project_update_from_grill_or_NOT_RUN`.
Report a Gate ledger for durable writes or skipped checks.
