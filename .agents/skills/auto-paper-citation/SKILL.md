---
name: auto-paper-citation
description: "Internal Harness instruction source for auto-paper-citation. Route through visible Harness aliases or hook contracts instead of invoking directly."
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
- candidate references extracted from PDF or Markdown notes

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

For blogs, reviews, surveys, and tutorials, every external factual claim,
named method, named dataset, named system, clinical-effectiveness claim,
economic claim, benchmark claim, and history/trend claim needs either a
verified citation row or an explicit `unsupported` / `metadata_only` row with a
revision action. Do not treat "blog" as permission to omit citations.

If the only available reference source is an AI dialogue, a PDF conversation,
or notes that quote literature without primary-source verification, extract the
candidate paper metadata into `citation_support_bank.md` with `support_grade:
metadata_only` or `partial` as appropriate and set
`needs_user_confirmation: yes`.

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
