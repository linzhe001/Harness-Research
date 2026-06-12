---
name: auto-paper-patch
description: "Internal Harness instruction source for auto-paper-patch. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper Patch

## Purpose

Produce bounded LaTeX changes from approved artifacts. In a guarded Harness
workspace, default to writing apply-ready diffs under
`auto_paper_output/<paper_id>/` instead of directly editing the manuscript
source. Do not perform broad rewrites from chat memory.

## Required Inputs

- `latex_patch_plan.md`
- `writing_rationale_matrix.md`
- `claim_register.md`
- `citation_support_bank.md`
- current draft files

## Patch Policy

- Generate one section or contiguous unit group at a time.
- Write `latex_patch.diff` or `patches/<unit_id>.diff` plus `patch_ledger.md`
  by default.
- Direct `.tex` or `.bib` edits are allowed only when the operator explicitly
  authorizes applying a patch and the active workspace write scope permits the
  target path.
- Preserve labels, refs, citation keys, graphics paths, tables, equations,
  environments, macros, and venue wrappers unless the patch plan explicitly
  says otherwise.
- Do not add citation keys that are absent from `citation_support_bank.md`.
- Do not delete citation keys still used by a registered claim.
- Do not strengthen unsupported claims for fluency.

## Outputs

Write:

- `latex_patch.diff` or `patches/<unit_id>.diff`
- `patch_ledger.md`
- guard or compile reports when the patch was applied in a temporary copy

`patch_ledger.md` rows must include:

- file path
- line anchor
- before role
- after role
- rationale row
- claim IDs
- citation IDs
- patch artifact
- guard result
- reviewer-risk delta

Run `.agents/skills/auto-paper/scripts/latex_guard.py` on an applied temporary
copy when possible. If no temporary apply step is run, record
`guard_result: NOT_RUN` with the reason.
