---
name: auto-paper-patch
description: Run the auto-paper patch phase. Use as the only branch that may edit LaTeX or bibliography files, applying bounded changes from latex_patch_plan.md and writing patch_ledger.md with guard results.
---

# Auto Paper Patch

## Purpose

Apply bounded LaTeX changes from approved artifacts. Do not perform broad
rewrites from chat memory.

## Required Inputs

- `latex_patch_plan.md`
- `writing_rationale_matrix.md`
- `claim_register.md`
- `citation_support_bank.md`
- current draft files

## Patch Rules

- Patch one section or contiguous unit group at a time.
- Preserve labels, refs, citation keys, graphics paths, tables, equations,
  environments, macros, and venue wrappers unless the patch plan explicitly
  says otherwise.
- Do not add citation keys that are absent from `citation_support_bank.md`.
- Do not delete citation keys still used by a registered claim.
- Do not strengthen unsupported claims for fluency.

## Outputs

Write `patch_ledger.md` rows with:

- file path
- line anchor
- before role
- after role
- rationale row
- claim IDs
- citation IDs
- guard result
- reviewer-risk delta

After each patch, run `.agents/skills/auto-paper/scripts/latex_guard.py` when
available and the configured compile command when appropriate.
