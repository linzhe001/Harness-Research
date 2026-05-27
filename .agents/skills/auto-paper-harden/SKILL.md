---
name: auto-paper-harden
description: Run the auto-paper harden phase. Use for final manuscript audit, artifact completeness, claim support, logic transfer, revision quality, LaTeX guard, compile report, and reviewer-risk gate routing.
---

# Auto Paper Harden

## Purpose

Audit manuscript readiness. Do not do large rewrites in harden; route failures
to the owning phase.

## Required Inputs

- R/A/C/L/P phase artifacts
- patched TeX files
- bibliography files
- guard or compile reports when present

## Audits

Artifact completeness checks required files, non-empty content, identifiers,
and cross-references.

Logic transfer compares `original_logic_map.md`,
`writing_rationale_matrix.md`, and revised TeX to detect lost logic or shallow
substitution.

Claim support checks every claim against author evidence or
`citation_support_bank.md`, including over-strong verbs and missing
boundaries.

LaTeX and compile audit runs the static guard and configured compile command
when available.

Reviewer-risk audit covers motivation, novelty, evidence, baseline fairness,
method clarity, result interpretation, limitations, reproducibility,
ethics/data statements, and template compliance.

Use deterministic scripts where possible:

- `.agents/skills/auto-paper/scripts/artifact_check.py`
- `.agents/skills/auto-paper/scripts/integrity_audit.py`
- `.agents/skills/auto-paper/scripts/citation_bank_check.py`
- `.agents/skills/auto-paper/scripts/claim_register_check.py`
- `.agents/skills/auto-paper/scripts/revision_audit.py`
- `.agents/skills/auto-paper/scripts/style_metrics.py`
- `.agents/skills/auto-paper/scripts/latex_guard.py`

## Outputs

Write:

- `audit_report.md`
- `compile_report.md`
- `citation_audit_report.md`
- `revision_audit_report.md`
- `logic_transfer_audit.md`
- `final_gate_ledger.md`

Final decision must be one of `COMPLETE`, `USER_GATE`, `REWORK_RESEARCH`,
`REWORK_ARGUMENT`, `REWORK_CITATION`, `REWORK_LAYOUT`, `REWORK_PATCH`, or
`ABORT`.
