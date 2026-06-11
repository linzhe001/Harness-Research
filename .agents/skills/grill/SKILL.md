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
- Workflow/context/documentation/language rules under
  `../../../.agents/references/`

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
- maximum claim boundary and forbidden claims
- pivot / abort condition
- dataset source, access status, and local/private target when known
- baseline or negative-control source, including a code repository URL or
  `baseline_repo_missing`
- compute, budget, registration, and approval assumptions that would stop
  `prepare`

For datasets, require a direct downloadable source, official dataset API,
Hugging Face dataset id, release/archive URL, or private exact local path.
Paper pages, method pages, and project pages are contextual unless they expose
an acquisition source.

For baselines, require a concrete code repository URL, official code
entrypoint, or private exact local path. Method names and paper URLs are
non-executable until source provenance is known.

## Outputs

Grill may create or refresh:
- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `.workflow_supervisor/readiness.json` only through Grill/supervisor tooling

In `docs/Execution_Readiness_Packet.md`, keep three compact ledgers:

- `Dataset Access Ledger`: dataset id, source/entrypoint, access verdict,
  probe result, execution decision, notes.
- `Baseline Source Ledger`: baseline id/name, role, code repository URL or
  official code entrypoint, probe result, execution decision, notes.
- `Execution Intent Ledger`: acquisition and clone policy rows.

Execution decisions are `candidate`, `rejected`, `requires_approval`, or
`deferred`. Active rows must not remain `pending`; use blockers such as
`baseline_repo_missing`, `missing_dataset_source`, `requires_approval`, or
`deferred`.

For policy rows, use readiness input `kind: policy` and stable keys:
`hf_access_policy`, `non_hf_registration_policy`, `baseline_clone_policy`,
`baseline_clone_scope`, and `external_download_policy`. These are candidate
readiness inputs, not Approval Evidence or Approved Contracts.
When readiness JSON is written, also keep top-level structured fields:
`external_download_policy`, `approved_datasets`, `approved_baselines`,
`target_paths`, `unknowns`, and `operator_approved_at`.
Dataset rows may include `target`, `license`, and `max_size_gb`; baseline rows
may include `repo`, `ref`, and `target`.

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
accepted draft, continue with `$init-project update-from-grill` unless the
operator asks to skip guidance initialization. Inputs are the three Grill docs
and `.workflow_supervisor/readiness.json` when supervisor tooling produced it.

The handoff initializes or refreshes `CLAUDE.md`, `AGENTS.md`, and `README.md`
from candidate Grill context only, preserves `## Custom`, keeps dataset and
baseline items candidate until `prepare` / WF4-WF5 verify them, and must not
mark WF1-WF3 complete. If not run, report
`init_project_update_from_grill_or_NOT_RUN`.

Report a Gate ledger for durable writes or skipped checks.
