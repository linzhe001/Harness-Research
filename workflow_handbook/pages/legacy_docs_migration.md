---
schema_version: "0.1"
page_id: "legacy_docs_migration"
title: "Legacy Docs Migration"
kind: "how_to"
audience: ["agent", "maintainer", "operator"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/legacy_docs_migration.md"
source_of_truth: true
status: "current"
summary: "How agents should migrate older flat docs, numbered context docs, and contract text into dynamic-context-v2."
nav:
  section: "operate"
  position: 18
canonical_sources:
  - path: ".agents/references/context-layering-policy.md"
    role: "framework_rule"
  - path: ".agents/references/evidence-chain-rule.md"
    role: "framework_rule"
  - path: ".agents/references/contract-gating-rule.md"
    role: "framework_rule"
  - path: ".agents/references/commit-checkpoint-rule.md"
    role: "framework_rule"
references:
  - "term:Conclusion Evidence"
  - "term:Evidence Chain"
  - "term:Gate Evidence"
  - "term:Human Approval"
  - "page:evidence_approval_model"
  - "page:workflow_layers"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/legacy_docs_migration.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Legacy Docs Migration

## Goal

把旧 target workspace 里的 flat docs、旧 numbered context docs 和旧
contract 文本迁移到当前 `dynamic-context-v2` layout，同时保留 provenance，
避免把旧结论直接污染成 Current Facts、Approved Contracts 或 accepted
lessons。

Use this page when a target workspace has older files such as
`docs/Research_Intent_Draft.md`, `docs/Execution_Readiness_Packet.md`,
`docs/Feasibility_Report.md`, `docs/Technical_Spec.md`,
`docs/Baseline_Report.md`, `docs/10_contract/**`,
`docs/30_evidence/**`, `docs/40_iterations/Experiment_Queue.md`,
`docs/45_discoveries/Research_Wiki.md`, ad hoc contract sections, or old
memory notes.

## Prerequisites

- Read `AGENTS.md`, `CLAUDE.md`, `workflow_handbook/pages/workflow_layers.md`,
  `.agents/references/context-layering-policy.md`,
  `.agents/references/evidence-chain-rule.md`, and
  `.agents/references/contract-gating-rule.md`.
- Inspect `git status --short`; do not mix migration with unrelated code or
  experiment changes.
- Do not hand-edit `.evidence/**`, `.workflow_supervisor/**`,
  `.auto_iterate/**`, `docs/_views/**`, or `docs/_site/**`.
- Treat `docs/_views/**` and `docs/_site/**` as generated reading views, not
  migration inputs. Migrate and review the source Markdown first.
- Treat old docs as source artifacts until reclassified. Do not assume old
  `approved`, `final`, or `validated` wording is current Human Approval.

## Steps

1. Inventory the old docs before editing:

```bash
find docs -maxdepth 3 -type f | sort
git status --short
```

Classify each file into one target layer. The canonical v2 destinations are
under `docs/context/`; old numbered directories are migration sources or
archive paths unless the project explicitly remains legacy:

| Old content | New destination | Rule |
| --- | --- | --- |
| Grill/intake drafts | `docs/05_intake/**` | Candidate context only. |
| Approved or proposed contract text | `docs/context/contracts.md` | Draft unless current Approval Evidence exists. |
| Current code, data, environment, dataset, or baseline facts | `docs/context/facts.md` | Must cite current source artifacts. |
| Tables of papers, baselines, metrics, datasets, open questions | `docs/context/evidence.md` | Conclusion Evidence inputs, not approval. |
| Protocol procedure, metric plan, failure modes | `docs/context/protocol.md` | Protocol Draft until approved. |
| Iteration/run summaries | `iteration_log.json` and `docs/context/experiments.md` | Keep run IDs and artifact refs. |
| Planned experiments, falsifiers, controls, run requests, assurance gaps | `docs/context/experiments.md` | Experiment Queue section, not Conclusion Evidence by itself. |
| Observations, phenomena, hypotheses, next-run hints | `docs/context/experiments.md` | Mutable discovery section. |
| Searchable findings, method notes, paper context, open questions | `docs/context/experiments.md` | Research Wiki section, not Approved Contract. |
| Candidate or accepted lessons | `docs/context/memory.md`; `MEMORY.md` only for accepted lessons if the project keeps a root lessons bank | Follow lesson-quality rule. |
| Superseded narrative docs | `docs/90_legacy/**` | Preserve for audit, do not load by default. |

2. Initialize v2 context docs and migrate legacy inputs:

```bash
python tooling/evidence/init_context.py --workspace-root . --set-state
python tooling/evidence/migrate_context_v2.py --workspace-root . --overwrite
```

Use `--archive-old` on `migrate_context_v2.py` only when the operator wants
the old numbered docs moved under `docs/90_legacy/**` in the same migration
slice. Otherwise leave old docs in place as compatibility inputs until the
migration result is reviewed.

3. Move old Grill files without changing their meaning:

```text
docs/Research_Intent_Draft.md -> docs/05_intake/Research_Intent_Draft.md
docs/Grill_Round_Log.md -> docs/05_intake/Grill_Round_Log.md
docs/Execution_Readiness_Packet.md -> docs/05_intake/Execution_Readiness_Packet.md
```

If a target file already exists, merge by preserving both timestamps and
operator decisions. Do not overwrite `## Custom` sections.

4. Rebuild contract sections as drafts unless approval is current and auditable.

Use this destination:

```text
docs/context/contracts.md
```

When migrating old contract content:

- Copy the original claim or boundary under a `Migrated Source` or `Prior Text`
  section.
- Set the matching named status header to `draft` when Approval Evidence is
  absent, stale, ambiguous, or only implied by old prose, for example
  `Evaluation Contract status: draft`.
- Preserve explicit approval provenance when it exists, but verify it against
  the current `PROJECT_STATE.json.contracts.*` record before treating it as
  approved.
- If content changes after approval, mark it `draft` or `superseded` and seek a
  new Review Packet decision.

5. Compile current contract, fact, and protocol docs with explicit sources.

For each migrated current doc under `docs/context/*.md`, run `compile_doc.py`
with the old doc and any source artifacts that support the migrated claims:

```bash
python tooling/evidence/compile_doc.py \
  --workspace-root . \
  --doc docs/context/contracts.md \
  --source docs/90_legacy/Old_Evaluation_Notes.md \
  --source docs/Baseline_Report.md
```

Use `compile_protocol.py` when evidence tables should regenerate
`docs/context/protocol.md`. Use `approve_contract.py` only after explicit
current Human Approval.

6. Migrate mutable observations before promoting lessons.

Put planned experiments, falsifiers, controls, paper-driven run requests, and
Assurance Axis gaps into the Experiment Queue section of
`docs/context/experiments.md`. Put raw run observations, surprising patterns,
hypotheses, and next-experiment hints into the mutable discovery section of the
same file. Put searchable findings, method notes, paper context, and open
questions into the Research Wiki section. Promote only reviewed lesson
candidates to `docs/context/memory.md`; write `MEMORY.md` only for accepted
lessons with scope, evidence refs, alternatives, and future action when the
project keeps a root lessons bank.

7. Archive superseded files instead of deleting them:

```text
docs/90_legacy/<original_name>.md
```

Keep a short migration note in the new file or in `docs/90_legacy/README.md`
that says which new file replaced it. Do not archive generated views or
tool-owned runtime state.

8. Refresh compact evidence and gates:

```bash
python tooling/evidence/build_light_evidence_index.py --workspace-root .
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
```

Use the stage that matches the next decision (`wf5`, `wf10`, `wf11`, or
`wf12`). If a tool cannot run, report `NOT_RUN` with the reason.
Do not make `docs/_views/**` or `docs/_site/**` part of the migration slice.
If the operator explicitly wants refreshed generated views, run the owning
renderer as a separate docs-site slice and record `docs_site_boundary_report`;
otherwise leave generated views unchanged.

9. Create a docs commit checkpoint.

Use the `docs` validation profile from
`.agents/references/commit-checkpoint-rule.md`. Stage only the migration slice,
not unrelated experiment or implementation changes.

## Expected Outputs

- `docs/05_intake/**` contains only mutable intake candidates.
- `docs/context/contracts.md` contains draft or approved contract sections with
  explicit named approval state.
- `docs/context/facts.md`, `docs/context/evidence.md`, and
  `docs/context/protocol.md` contain current facts, Conclusion Evidence inputs,
  and Protocol Drafts.
- `docs/context/experiments.md` contains pending experiment questions,
  falsifiers, controls, run requests, assurance gaps, mutable discoveries,
  searchable findings, method notes, paper context, and open questions.
- `docs/context/memory.md` and optional root `MEMORY.md` contain only promoted
  lessons at the correct maturity level.
- `docs/90_legacy/**` preserves superseded narrative docs.
- Gate ledger reports the exact commands run and whether each was `PASS`,
  `FAIL`, or `NOT_RUN`.

## Gates

Run the narrowest relevant checks:

```bash
python tooling/evidence/validate_workflow_handbook.py --workspace-root .
pytest -q tooling/.tests/test_workflow_handbook_site.py
```

For target workspaces, use the dynamic-context gates that match the migrated
docs:

```bash
python tooling/evidence/check_dynamic_context.py --workspace-root . --stage wf10 --review-packet
python tooling/evidence/check_docchain_gates.py --workspace-root .
python tooling/evidence/build_light_evidence_index.py --workspace-root .
```

When a contract approval is involved, do not report readiness unless the Review
Packet and Approval Evidence are current. When a claim or claim boundary changes
inside an accepted Automation Policy, record Claim Delta Evidence and Gate
ledger output; request Human Approval only when the change leaves the policy or
uses an approval-recording tool.

## Troubleshooting

- Old doc says `approved`, but no approval record exists:
  migrate as `Status: draft`, cite the old doc as a Source Artifact, and request
  Review Packet approval.
- Old protocol conflicts with newer runs:
  keep the old text under `docs/90_legacy/**`, record the conflict in
  `docs/context/protocol.md`, and put the observed pattern in
  `docs/context/experiments.md`.
- Old memory contains raw observations:
  move observations to `docs/context/experiments.md`; promote only scoped
  lessons through `docs/context/memory.md`.
- Evidence chain fails because sources are missing:
  mark the migrated claim as an open question or low-confidence draft. Do not
  invent source paths or approval.
- Dirty worktree spans multiple owners:
  split the migration into Commit Slices and checkpoint each slice.
