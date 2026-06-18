---
name: auto-paper-argument
description: "Internal Harness instruction source for auto-paper-argument. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper Argument

## Purpose

Decide what the paper can responsibly claim. Do not optimize sentences and do
not patch LaTeX in this phase.

## Required Inputs

- `research_dossier.md`
- `exemplar_learning_dossier.md`
- `style_profile.md`
- `sota_gap_map.md`
- `../../../.agents/references/research-supervision-patterns.md`
- `../../../.agents/references/research-supervision/idea-evaluation.md`
- `../../../.agents/references/research-supervision/paper-writing-layouts.md`
- `../../../.agents/references/research-supervision/case-patterns.md`
- operator brief or approved claim boundary when present

## Confirmed Motivation

`confirmed_motivation.md` must include:

- `one_sentence_argument`
- `paper_type` and `dominant_improvement_axis` when inferable from evidence
- `field_need`
- `unresolved_bottleneck`
- `proposed_move`
- `decisive_evidence`
- `broader_implication`
- `boundary`
- `claims_to_avoid`

## Claim Register

Each row in `claim_register.md` should include:

- `claim_id`
- `location`
- `claim_text`
- `evidence_source`
- `citation_need`
- `verb_strength`
- `scope_limit`
- `reviewer_risk`

If a central claim depends on operator intent or missing evidence, return
`USER_GATE` with at most three questions.

## Outputs

Write:

- `confirmed_motivation.md`
- `claim_register.md`
- `claims_to_avoid.md`
- `motivation_surface_map.md`

Run the deterministic claim gate before handing off to citation. This pass
checks claim schema, author evidence, and scope boundaries; rerun it with
`--citation-bank` after citation if citation support exists.

- `.agents/skills/auto-paper/scripts/claim_register_check.py auto_paper_output/<paper_id>/claim_register.md`

## Gate Ledger

Report a Gate ledger entry with commands run, artifacts written, claim-gate
result, any `USER_GATE` or `NOT_RUN` reason, and the next owner before handoff.
