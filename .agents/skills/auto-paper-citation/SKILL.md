---
name: auto-paper-citation
description: Run the auto-paper citation phase. Use to segment manuscript claims, build a citation support bank, grade support strength, map claims to citations, and route unsupported claims before LaTeX patching.
---

# Auto Paper Citation

## Purpose

Support claims, not reference stuffing. Do not rewrite the manuscript in this
phase.

## Required Inputs

- `claim_register.md`
- bibliography files from `config.yaml`
- `research_dossier.md`
- optional local reference PDFs or external search results

## Support Grades

Use the grades from
`.agents/skills/auto-paper/references/citation-support-bank.md`:

- `strong`
- `partial`
- `background`
- `limiting`
- `metadata_only`
- `unsupported`

`metadata_only` is never claim support.

## Outputs

Write:

- `citation_support_bank.md`
- `claim_citation_map.md`
- optional `citation_audit_report.md`

Run the deterministic support-bank gate when the bank is drafted:

- `.agents/skills/auto-paper/scripts/citation_bank_check.py auto_paper_output/<paper_id>/citation_support_bank.md`

If a core claim has only `background`, `metadata_only`, or `unsupported`
support, route back to citation or argument instead of adding a weak citation
during patch.

## Gate Ledger

Report a Gate ledger entry with commands run, artifacts written, support-bank
gate result, any `USER_GATE` or `NOT_RUN` reason, and the next owner before
handoff.
