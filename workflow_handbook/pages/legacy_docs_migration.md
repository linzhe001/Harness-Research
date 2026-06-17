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
summary: "How agents should migrate older flat docs and contract text into the current Harness context layout."
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

把旧 target workspace 里的 flat docs 和旧 contract 文本迁移到当前 Harness
layout，同时保留 provenance，避免把旧结论直接污染成 Current Facts、Approved
Contracts 或 `MEMORY.md` lessons。

Use this page when a target workspace has older files such as
`docs/Research_Intent_Draft.md`, `docs/Execution_Readiness_Packet.md`,
`docs/Feasibility_Report.md`, `docs/Technical_Spec.md`,
`docs/Baseline_Report.md`, ad hoc contract sections, or old memory notes.

## Prerequisites

- Read `AGENTS.md`, `CLAUDE.md`, `workflow_handbook/pages/workflow_layers.md`,
  `.agents/references/context-layering-policy.md`,
  `.agents/references/evidence-chain-rule.md`, and
  `.agents/references/contract-gating-rule.md`.
- Inspect `git status --short`; do not mix migration with unrelated code or
  experiment changes.
- Do not hand-edit `.evidence/**`, `.workflow_supervisor/**`,
  `.auto_iterate/**`, `docs/_views/**`, or `docs/_site/**`.
- Treat old docs as source artifacts until reclassified. Do not assume old
  `approved`, `final`, or `validated` wording is current Human Approval.

## Steps

1. Inventory the old docs before editing:

```bash
find docs -maxdepth 3 -type f | sort
git status --short
```

Classify each file into one target layer:

| Old content | New destination | Rule |
| --- | --- | --- |
| Grill/intake drafts | `docs/05_intake/**` | Candidate context only. |
| Approved or proposed contract text | `docs/10_contract/**` | Draft unless current Approval Evidence exists. |
| Current code, data, environment, dataset, or baseline facts | `docs/20_facts/**` or legacy report | Must cite current source artifacts. |
| Tables of papers, baselines, metrics, datasets, open questions | `docs/30_evidence/**` | Conclusion Evidence inputs, not approval. |
| Protocol procedure, metric plan, failure modes | `docs/35_protocol/**` | Protocol Draft until approved. |
| Iteration/run summaries | `docs/40_iterations/**` and `iteration_log.json` | Keep run IDs and artifact refs. |
| Observations, phenomena, hypotheses, next-run hints | `docs/45_discoveries/Discovery_Ledger.md` | Mutable discovery layer. |
| Candidate or accepted lessons | `docs/50_memory/Lessons.md`; `MEMORY.md` only for accepted lessons | Follow lesson-quality rule. |
| Superseded narrative docs | `docs/90_legacy/**` | Preserve for audit, do not load by default. |

2. Create the new directories if missing:

```bash
mkdir -p docs/05_intake docs/10_contract docs/20_facts docs/30_evidence \
  docs/35_protocol docs/40_iterations docs/45_discoveries docs/50_memory \
  docs/90_legacy
```

3. Move old Grill files without changing their meaning:

```text
docs/Research_Intent_Draft.md -> docs/05_intake/Research_Intent_Draft.md
docs/Grill_Round_Log.md -> docs/05_intake/Grill_Round_Log.md
docs/Execution_Readiness_Packet.md -> docs/05_intake/Execution_Readiness_Packet.md
```

If a target file already exists, merge by preserving both timestamps and
operator decisions. Do not overwrite `## Custom` sections.

4. Rebuild contract docs as drafts unless approval is current and auditable.

Use these destinations:

```text
docs/10_contract/Project_Contract.md
docs/10_contract/Evaluation_Contract.md
docs/10_contract/Baseline_Contract.md
docs/10_contract/Claim_Boundary.md
```

When migrating old contract content:

- Copy the original claim or boundary under a `Migrated Source` or `Prior Text`
  section.
- Set `Status: draft` when Approval Evidence is absent, stale, ambiguous, or
  only implied by old prose.
- Preserve explicit approval provenance when it exists, but verify it against
  the current `PROJECT_STATE.json.contracts.*` record before treating it as
  approved.
- If content changes after approval, mark it `draft` or `superseded` and seek a
  new Review Packet decision.

5. Compile current contract, fact, and protocol docs with explicit sources.

For each migrated current doc under `docs/10_contract/**`,
`docs/20_facts/**`, or `docs/35_protocol/**`, run `compile_doc.py` with the old
doc and any source artifacts that support the migrated claims:

```bash
python tooling/evidence/compile_doc.py \
  --workspace-root . \
  --doc docs/10_contract/Evaluation_Contract.md \
  --source docs/90_legacy/Old_Evaluation_Notes.md \
  --source docs/Baseline_Report.md
```

Use `compile_protocol.py` when evidence tables should regenerate
`docs/35_protocol/**`. Use `approve_contract.py` only after explicit current
Human Approval.

6. Migrate mutable observations before promoting lessons.

Put raw run observations, surprising patterns, hypotheses, and next-experiment
hints into `docs/45_discoveries/Discovery_Ledger.md`. Promote only reviewed
lesson candidates to `docs/50_memory/Lessons.md`; write `MEMORY.md` only for
accepted lessons with scope, evidence refs, alternatives, and future action.

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

9. Create a docs commit checkpoint.

Use the `docs` validation profile from
`.agents/references/commit-checkpoint-rule.md`. Stage only the migration slice,
not unrelated experiment or implementation changes.

## Expected Outputs

- `docs/05_intake/**` contains only mutable intake candidates.
- `docs/10_contract/**` contains draft or approved contract docs with explicit
  approval state.
- `docs/20_facts/**`, `docs/30_evidence/**`, and `docs/35_protocol/**` contain
  current facts, Conclusion Evidence inputs, and Protocol Drafts.
- `docs/45_discoveries/Discovery_Ledger.md` contains mutable discoveries.
- `docs/50_memory/Lessons.md` and `MEMORY.md` contain only promoted lessons at
  the correct maturity level.
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

When a contract or claim boundary is involved, do not report readiness unless
the Review Packet and Approval Evidence are current.

## Troubleshooting

- Old doc says `approved`, but no approval record exists:
  migrate as `Status: draft`, cite the old doc as a Source Artifact, and request
  Review Packet approval.
- Old protocol conflicts with newer runs:
  keep the old text under `docs/90_legacy/**`, record the conflict in
  `docs/35_protocol/Protocol_Changelog.md`, and put the observed pattern in
  `docs/45_discoveries/Discovery_Ledger.md`.
- Old memory contains raw observations:
  move observations to `docs/45_discoveries/Discovery_Ledger.md`; promote only
  scoped lessons through `docs/50_memory/Lessons.md`.
- Evidence chain fails because sources are missing:
  mark the migrated claim as an open question or low-confidence draft. Do not
  invent source paths or approval.
- Dirty worktree spans multiple owners:
  split the migration into Commit Slices and checkpoint each slice.
