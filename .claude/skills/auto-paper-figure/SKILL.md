# Auto Paper Figure

<instructions>
1. Read figure assets, source data, `claim_register.md`,
   `citation_support_bank.md`, `tex_inventory.json`, and venue figure rules.
2. Write `figure_asset_map.md`, `figure_contract.md`,
   `caption_claim_map.md`, and `figure_backend_report.md` under
   `auto_paper_output/<paper_id>/`.
3. Map every quantitative or qualitative caption claim to registered evidence
   or citation support.
4. Do not generate plots from unverified data paths or inferred metrics.
5. Return `USER_GATE` when plotting or caption claims lack source evidence.
6. Report a Gate ledger entry with commands run, artifacts written,
   figure/caption gate result, any `USER_GATE` or `NOT_RUN` reason, and the
   next owner before handoff.
</instructions>
