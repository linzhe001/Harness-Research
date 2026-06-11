---
name: grill
description: "Clarify early research intent through hard questions and produce draft-only Research Intent, Grill Round Log, and Execution Readiness Packet artifacts. Does not approve contracts or complete WF1-WF3 by itself."
argument-hint: "[seed idea or --bridge-stages]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Grill

Use `/grill` for high-interaction research intent clarification before
execution automation. It writes draft-only intent/readiness artifacts and must
not approve contracts or mark WF1-WF3 complete without the canonical Stage
artifacts and Gate ledger.

Grill is conversation-first. Start by restating the current intent in one short
paragraph, then ask 3-5 blocking questions that would change the next safe
action. Each question must include why it matters. Do not begin with a polished
draft, approval, or long questionnaire.

Every Grill round must leave an operator answer summary, critique lens,
current gap check, next blocking question or explicit exit choice, exit
recommendation, and human exit decision status. The operator owns the exit
decision. You may recommend `continue_grill`, `grill_draft_ready`,
`bridge_wf1_wf3`, `pivot`, or `abandon`, but must not declare the decision
unless the operator made it in the current conversation or an auditable
artifact.

The handoff target is candidate-clear intent: concrete observation, candidate
claim, falsifier, metric/evaluation signal, baseline or negative control,
dataset/compute assumptions, maximum claim boundary, forbidden claims,
pivot/abort condition, and execution readiness inputs that would otherwise
stop `prepare`. Executable baselines need a code repository URL, official code
entrypoint, or exact local path; executable datasets need a direct downloadable
source, official dataset API, Hugging Face dataset id, release/archive URL, or
exact local path in private readiness. Missing items stay as unresolved
questions.

Read the compact workflow/supervisor runtime reference, workflow guide, context
layering, contract gating, documentation rules, language policy, and
ubiquitous language before durable edits. Keep exact local/private values in
`.workflow_supervisor/readiness.json` through tooling; redact public Markdown.
When datasets are discussed, record a structured `Dataset Access Ledger` or
equivalent table in `docs/Execution_Readiness_Packet.md`: dataset id, source
URL or official entrypoint, access verdict, non-destructive download probe,
execution decision, and notes. Execution decision must be explicit:
`candidate`, `rejected`, `requires_approval`, or `deferred`. Use repository,
API, README, HTTP HEAD, or file-list probes when feasible, but do not download
large assets, private assets, or non-approved gated datasets during Grill;
`prepare` / WF4 performs actual acquisition and records download Gate
Evidence.

For active data or baseline readiness, ask for executable source provenance
instead of accepting method names. A dataset is executable only when Grill has
found a direct download/acquisition source such as a Hugging Face dataset id,
official dataset API, repository/release/archive URL, Zenodo record, or exact
local path kept in readiness JSON. A baseline is executable only when Grill has
found a concrete code repository URL, official code entrypoint, or exact local
path. Paper pages, method pages, project pages without code, benchmark names,
and reported-method baselines are contextual only; record them as non-executable
or as a `baseline_repo_missing` / dataset-source blocker until the acquisition
source is found. Record baseline candidates in a `Baseline Source Ledger` or
equivalent table with baseline id/name, role, code repository URL or official
code entrypoint, repo/code probe result, execution decision, and notes.
Before recommending or accepting `grill_draft_ready`, make sure
`docs/Execution_Readiness_Packet.md` has non-placeholder Execution Intent,
Dataset Access, and Baseline Source ledgers. Every active dataset and executable
baseline/negative control must have either a concrete acquisition source plus
`Execution Decision: candidate`, or an explicit non-executable decision such as
`deferred`, `requires_approval`, `rejected`, or `baseline_repo_missing`.

When external acquisition, clone, or access intent is discussed, also record an
`Execution Intent Ledger` in `docs/Execution_Readiness_Packet.md` and mirror the
same intent as machine-readable readiness inputs when
`.workflow_supervisor/readiness.json` is written through Grill tooling. Use
stable keys so `prepare --complete` can consume them without guessing from
prose: `hf_access_policy` for source-specific Hugging Face allowance with no
credentials or tokens, `non_hf_registration_policy` for non-HF gated-source
exclusion or later-approval rules, `baseline_clone_policy` for clone allowance,
`baseline_clone_scope` for the concrete first baseline set such as
`Free-SurGS, Feature 3DGS`, and `external_download_policy` only for an
intentionally broad global external download/clone policy. Use readiness input
`kind: policy`. These rows are candidate readiness policy, not Approval
Evidence or Approved Contracts; deferred, rejected, or `requires_approval`
dataset rows remain non-executable until later explicit approval expands scope.
Do not leave active acquisition rows as `pending` at handoff; record the
intended acquisition mode such as Hugging Face auth download, local path
verification, Git clone, release/archive download, or no-download reference
inspection.
When readiness JSON is written, keep top-level structured fields:
`external_download_policy`, `approved_datasets`, `approved_baselines`,
`target_paths`, `unknowns`, and `operator_approved_at`.
Dataset rows may include `target`, `license`, and `max_size_gb`; baseline rows
may include `repo`, `ref`, and `target`.

Outputs:
- `docs/Research_Intent_Draft.md`
- `docs/Grill_Round_Log.md`
- `docs/Execution_Readiness_Packet.md`
- `.workflow_supervisor/readiness.json` only when Grill readiness tooling is
  run with a write action, or when supervisor tooling produces it

Prefer helper commands for durable draft writes:
- `python tooling/grill/questions.py --lens intake`
- `python tooling/grill/draft.py --workspace-root . init --seed "<idea>"`
- `python tooling/grill/draft.py --workspace-root . round --lens skeptic --answer-summary "<summary>" --gap-check "<gap>" --next-question "<question>" --exit-recommendation continue_grill`
- `python tooling/grill/draft.py --workspace-root . packet --readiness-json <path>`
- `python tooling/grill/readiness.py --workspace-root . --check --verify-paths --json`
- `python tooling/grill/readiness.py --workspace-root . --write-readiness --input-json <path> --json`

Use `--write-readiness` only when intentionally writing supervisor-owned
`.workflow_supervisor/readiness.json` through tooling.
Grill does not create `PROJECT_STATE.json`, `project_map.json`, or
`iteration_log.json`; those are owned by later workflow/state tooling, stable
build planning, and WF10 iteration.

When the operator explicitly confirms `grill_draft_ready` or asks to proceed
from an accepted Grill draft, continue in the same turn with
`/init-project update-from-grill` unless the operator asks to skip guidance
initialization. The handoff reads `docs/Research_Intent_Draft.md`,
`docs/Grill_Round_Log.md`, `docs/Execution_Readiness_Packet.md`, and
`.workflow_supervisor/readiness.json` when supervisor tooling has produced it.
It initializes or refreshes `CLAUDE.md`, `AGENTS.md`, and `README.md` from
candidate Grill context only; dataset and baseline items remain candidate
until `prepare` / WF4-WF5 verify them. Do not mark WF1-WF3 complete from this
handoff, and do not create `PROJECT_STATE.json`, `project_map.json`, or
`iteration_log.json`. If the handoff is skipped, report
`init_project_update_from_grill_or_NOT_RUN` with the reason.

Exit with `grill_draft_ready`, `grill_bridge_complete`, `pivot`, or `abandon`,
and report Gate Evidence for durable writes or skipped checks. A
`grill_draft_ready` exit requires executable and non-executable acquisition
sources to be separated in the readiness ledgers, and
`/init-project update-from-grill` to have run or to be reported as `NOT_RUN`.
