---
name: auto-paper-argument
description: Run the auto-paper argument phase. Use to define central tension, core contribution, allowed novelty, claim boundaries, claim register, claims to avoid, and motivation surface map before citation or layout work.
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
- operator brief or approved claim boundary when present

## Confirmed Motivation

`confirmed_motivation.md` must include:

- `one_sentence_argument`
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
