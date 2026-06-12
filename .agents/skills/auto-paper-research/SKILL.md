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

## Workstreams

Scene Analyst reads the current draft, results, figures, tables, notes, and
repo docs. It outputs author evidence, known claims, known gaps, missing files,
and source provenance.

Exemplar Learner reads reference papers. It outputs section ordering,
paragraph moves, style profile, and useful sentence functions. It must not
create author claims.

SOTA Mapper reads bibliography, related-work notes, and optional external
search results when the user explicitly requested search. It outputs field map,
comparison axes, candidate citations, and unsupported areas.

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
