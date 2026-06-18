# Auto Paper Figure

<instructions>
1. Read `figure_requirement_scan.md` when present, figure assets, source data,
   `claim_register.md`, `citation_support_bank.md`, `tex_inventory.json`, and
   venue figure rules.
2. Write `figure_asset_map.md`, `figure_contract.md`,
   `caption_claim_map.md`, and `figure_backend_report.md` under
   `auto_paper_output/<paper_id>/`. Classify planned figures using
   `.claude/shared/research-supervision-patterns.md` and
   `.claude/shared/research-supervision/scientific-plotting.md`.
3. Map every quantitative or qualitative caption claim to registered evidence
   or citation support.
4. Conceptual review figures are allowed, but their captions must be framed as
   synthesis or route hypotheses and cite the source claims they visualize.
5. Do not generate plots from unverified data paths or inferred metrics.
6. If a PDF proposes a figure but quantitative panel data are absent, keep the
   figure as a conceptual schematic, mark the quantitative panel `USER_GATE`,
   or write `RUN_REQUEST` when the missing data is an experiment artifact.
7. Return `USER_GATE` when plotting or caption claims lack source evidence.
8. Report a Gate ledger entry with commands run, artifacts written,
   figure/caption gate result, any `USER_GATE` or `NOT_RUN` reason, and the
   next owner before handoff.
</instructions>
