---
name: auto-paper-research
description: "Internal Harness instruction source for auto-paper-research. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper Research

## Purpose

Build research context only. Do not patch `.tex`, write final sentences, or add
claims that are not supported by author evidence.

## Required Inputs

- `config.yaml`
- `source_index.md`
- `tex_inventory.json`
- local materials and draft sources named by intake
- `docs/30_evidence/Experiment_Evidence_Index.{json,md}` when present

## Workstreams

Scene Analyst reads the current draft, results, figures, tables, notes, repo
docs, and the experiment evidence index when present. It outputs author
evidence, known claims, known gaps, missing files, and source provenance. It may
read `iteration_log.json` as a weak signal for experiment intent, but must
cross-check purpose and result summaries against iteration reports, configs,
logs, metrics, or run artifacts before using them for paper claims.

When source PDFs or Markdown notes include figure/table suggestions, extract
the proposed visual purpose, evidence source, required data, and uncertainty
into `research_dossier.md` and `figure_requirement_scan.md`. Treat figure
requirements as writing context even when no image asset exists yet.

Exemplar Learner reads reference papers. It outputs section ordering,
paragraph moves, style profile, and useful sentence functions. It must not
create author claims.

SOTA Mapper reads bibliography, related-work notes, and optional external
search results when the user explicitly requested search. It outputs field map,
comparison axes, candidate citations, and unsupported areas.

For review/blog work, SOTA Mapper must produce citation candidates for all
named papers, methods, datasets, systems, and quantitative literature claims.
If candidates come from an AI dialogue or unverified PDF notes, mark them as
unverified candidates instead of omitting them.

## Outputs

Write:

- `research_dossier.md`
- `exemplar_learning_dossier.md`
- `style_profile.md`
- `sota_gap_map.md`

Every fact that may support later claims must carry provenance to local source,
TeX, bibliography, or the user brief.

## Gate Ledger

Report a Gate ledger entry with commands run, artifacts written, unresolved
source gaps, any `USER_GATE` or `NOT_RUN` reason, and the next owner before
handoff.
