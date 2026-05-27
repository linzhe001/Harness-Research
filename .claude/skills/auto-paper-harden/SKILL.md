---
name: auto-paper-harden
description: Run the auto-paper harden phase. Use for final manuscript audit, artifact completeness, claim support, logic transfer, revision quality, LaTeX guard, compile report, and reviewer-risk gate routing.
argument-hint: "[artifact dir]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Auto Paper Harden

<instructions>
1. Audit all R/A/C/L/P artifacts, patched TeX, bibliography, and guard reports.
2. Check artifact completeness, logic transfer, claim support, LaTeX/compile
   status, revision quality, and reviewer risk.
3. Do not perform large rewrites; route findings to the owning phase.
4. Write `audit_report.md`, `compile_report.md`,
   `citation_audit_report.md`, `revision_audit_report.md`,
   `logic_transfer_audit.md`, and `final_gate_ledger.md`.
5. Return `COMPLETE`, `USER_GATE`, a `REWORK_*` decision, or `ABORT`.
</instructions>
