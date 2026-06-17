# Auto Paper Citation

<instructions>
1. Read `claim_register.md`, bibliography files, research artifacts, local
   references, and candidate references extracted from PDF or Markdown notes.
2. Grade support as `strong`, `partial`, `background`, `limiting`,
   `metadata_only`, or `unsupported`.
3. Treat `metadata_only` as bibliographic metadata, not claim support.
4. For blogs, reviews, surveys, and tutorials, every external factual claim,
   named method, named dataset, named system, clinical-effectiveness claim,
   economic claim, benchmark claim, and history/trend claim needs either a
   verified citation row or an explicit `unsupported` / `metadata_only` row
   with a revision action.
5. If the only reference source is an AI dialogue, PDF conversation, or
   unverified literature note, extract candidate metadata into
   `citation_support_bank.md`, use `metadata_only` or `partial` as appropriate,
   and set `needs_user_confirmation: yes`.
6. Write `citation_support_bank.md`, `claim_citation_map.md`, and optional
   `citation_audit_report.md`.
7. Run `.agents/skills/auto-paper/scripts/citation_bank_check.py auto_paper_output/<paper_id>/citation_support_bank.md`.
8. Route weak core-claim support back to citation or argument before patching.
9. Report a Gate ledger entry with commands run, artifacts written,
   support-bank gate result, any `USER_GATE` or `NOT_RUN` reason, and the next
   owner before handoff.
</instructions>
