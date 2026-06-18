---
name: auto-paper-harden
description: "Internal Harness instruction source for auto-paper-harden. Route through visible Harness aliases or hook contracts instead of invoking directly."
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
- `../../../.agents/references/research-supervision-patterns.md`
- `../../../.agents/references/research-supervision/pre-submission-review.md`
- `../../../.agents/references/research-supervision/scientific-plotting.md`
- `docs/30_evidence/Experiment_Evidence_Index.{json,md}` when paper claims use
  experiment evidence

## Audits

Artifact completeness checks required files, non-empty content, identifiers,
and cross-references.

Logic transfer compares `original_logic_map.md`,
`writing_rationale_matrix.md`, and revised TeX to detect lost logic or shallow
substitution.

Claim support checks every claim against author evidence or
`citation_support_bank.md`, including over-strong verbs and missing
boundaries.

For blogs, reviews, surveys, and tutorials, citation audit must fail or route
back when named literature, clinical, economic, benchmark, dataset, or method
claims appear without citation support rows. A disclosure such as "source PDF
was not verified" is acceptable only as a boundary, not as a replacement for a
verified-reference plan.

Figure audit checks `figure_requirement_scan.md`, `figure_contract.md`,
`caption_claim_map.md`, and existing figure references. If the source material
asks for figures/tables but no figure contract exists, route to
`REWORK_LAYOUT` or `$auto-paper-figure` instead of declaring `COMPLETE`.

LaTeX and compile audit runs the static guard and configured compile command
when available.

Reviewer-risk audit covers motivation, novelty, evidence, baseline fairness,
method clarity, result interpretation, limitations, reproducibility,
ethics/data statements, and template compliance.
Also run the five-dimension pre-submission lens: macro logic, writing detail,
grammar/wording, format, and figure quality.

If a claim is blocked by missing or weak experiment evidence, write a concrete
request to `run_request_register.{json,md}` and return `RUN_REQUEST`. The
request must identify the blocking claim, needed evidence, experiment type,
minimum run artifacts, suggested `$run` prompt, and acceptance check. Do not
silently weaken or remove a central claim unless the operator approves that
tradeoff.

Use a strict analysis bar: if seed counts, raw metrics, statistical
comparisons, figure provenance, or comparison units are missing, mark the claim
as insufficiently supported and request the missing evidence instead of
polishing it into manuscript prose.

Use deterministic scripts where possible:

- `.agents/skills/auto-paper/scripts/artifact_check.py`
- `.agents/skills/auto-paper/scripts/integrity_audit.py`
- `.agents/skills/auto-paper/scripts/citation_bank_check.py`
- `.agents/skills/auto-paper/scripts/claim_register_check.py`
- `.agents/skills/auto-paper/scripts/figure_requirement_scan.py`
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
- `run_request_register.{json,md}` when `$run` needs to supply missing evidence

Final decision must be one of `COMPLETE`, `RUN_REQUEST`, `USER_GATE`,
`REWORK_RESEARCH`, `REWORK_ARGUMENT`, `REWORK_CITATION`, `REWORK_LAYOUT`,
`REWORK_PATCH`, or `ABORT`.
