# Auto Paper Harden

<instructions>
1. Audit all R/A/C/L/P artifacts, patched TeX, bibliography, and guard reports.
2. Check artifact completeness, logic transfer, claim support, LaTeX/compile
   status, revision quality, reviewer risk, macro logic, writing detail,
   grammar/wording, format, and figure quality using
   `.claude/shared/research-supervision/pre-submission-review.md` and
   `scientific-plotting.md`.
3. Prefer deterministic scripts: `artifact_check.py`, `integrity_audit.py`,
   `citation_bank_check.py`, `claim_register_check.py`,
   `figure_requirement_scan.py`, `revision_audit.py`, `style_metrics.py`, and
   `latex_guard.py`.
4. Do not perform large rewrites; route findings to the owning phase.
5. Write `audit_report.md`, `compile_report.md`,
   `citation_audit_report.md`, `revision_audit_report.md`,
   `logic_transfer_audit.md`, `final_gate_ledger.md`, and
   `run_request_register.{json,md}` when `/run` must supply missing evidence.
6. Return `RUN_REQUEST` when missing experiment evidence blocks a claim;
   include blocking claim, needed evidence, experiment type, minimum artifacts,
   suggested `/run` prompt, and acceptance check.
7. If seed counts, raw metrics, statistical comparisons, figure provenance, or
   comparison units are missing, mark the claim as insufficiently supported and
   request the missing evidence instead of polishing it into manuscript prose.
8. For blogs, reviews, surveys, and tutorials, route back when named
   literature, clinical, economic, benchmark, dataset, or method claims appear
   without citation support rows. A source-boundary disclosure is not a
   replacement for a verified-reference plan.
9. If source materials ask for figures/tables but no `figure_contract.md` and
   `caption_claim_map.md` exist, route to layout or `/auto-paper-figure`
   instead of declaring `COMPLETE`.
10. Return `COMPLETE`, `RUN_REQUEST`, `USER_GATE`, a `REWORK_*` decision, or
   `ABORT`.
</instructions>
