# Auto Paper Harden

<instructions>
1. Audit all R/A/C/L/P artifacts, patched TeX, bibliography, and guard reports.
2. Check artifact completeness, logic transfer, claim support, LaTeX/compile
   status, revision quality, and reviewer risk.
3. Prefer deterministic scripts: `artifact_check.py`, `integrity_audit.py`,
   `citation_bank_check.py`, `claim_register_check.py`,
   `revision_audit.py`, `style_metrics.py`, and `latex_guard.py`.
4. Do not perform large rewrites; route findings to the owning phase.
5. Write `audit_report.md`, `compile_report.md`,
   `citation_audit_report.md`, `revision_audit_report.md`,
   `logic_transfer_audit.md`, and `final_gate_ledger.md`.
6. Return `COMPLETE`, `USER_GATE`, a `REWORK_*` decision, or `ABORT`.
</instructions>
