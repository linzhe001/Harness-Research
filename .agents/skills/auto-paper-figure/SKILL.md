---
name: auto-paper-figure
description: "Internal Harness instruction source for auto-paper-figure. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper Figure

## Purpose

Create figure contracts and caption audits before any plotting or asset edits.
This branch is not the default drawing tool; enter it when the operator asks
for figure work, when TeX already references figures, when source PDFs or
Markdown notes mention needed figures/tables, or when harden finds
figure/caption risk.

## Required Inputs

- figure assets and source data when available
- `figure_requirement_scan.md` when source materials mention figures/tables
- current `claim_register.md`
- current `citation_support_bank.md`
- `tex_inventory.json` figure references
- `../../../.agents/references/research-supervision-patterns.md`
- `../../../.agents/references/research-supervision/scientific-plotting.md`
- target venue constraints for resolution, format, panels, and captions

## Outputs

Write under `auto_paper_output/<paper_id>/`:

- `figure_asset_map.md`
- `figure_contract.md`
- `caption_claim_map.md`
- `figure_backend_report.md`

## Rules

- Every quantitative or qualitative caption claim must map to a registered
  claim, local evidence item, or citation support row.
- Classify each planned figure as motivated example, solution overview,
  experimental result, or supporting figure.
- Conceptual review figures are allowed, but their caption must be framed as a
  synthesis or route hypothesis and must cite the source claims it visualizes.
- Do not generate new plots from unverified data paths or inferred metrics.
- If a PDF proposes a figure but the data needed for a quantitative panel is
  absent, keep the figure as a conceptual schematic, mark the quantitative panel
  `USER_GATE`, or write a `RUN_REQUEST` when the missing data is an experiment
  artifact.
- Preserve panel labels, file names, and LaTeX graphics references unless the
  patch plan explicitly changes them.
- If plotting is requested but inputs are incomplete, return `USER_GATE`.

## Gate Ledger

Report a Gate ledger entry with commands run, artifacts written, figure/caption
gate result, any `USER_GATE` or `NOT_RUN` reason, and the next owner before
handoff.
