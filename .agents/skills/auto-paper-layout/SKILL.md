---
name: auto-paper-layout
description: "Internal Harness instruction source for auto-paper-layout. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper Layout

## Purpose

Create an executable rewrite plan. Do not edit `.tex` files in layout.

## Required Inputs

- `tex_inventory.json`
- `confirmed_motivation.md`
- `claim_register.md`
- `citation_support_bank.md`
- `claim_citation_map.md`
- `figure_requirement_scan.md` when present
- `figure_contract.md` and `caption_claim_map.md` when figures are required
- `../../../.agents/references/research-supervision-patterns.md`
- `../../../.agents/references/research-supervision/paper-writing-layouts.md`
- `../../../.agents/references/research-supervision/benchmark-evaluation-paper.md`
- `../../../.agents/references/research-supervision/scientific-plotting.md`
- current draft snippets or line anchors

## Required Artifacts

`original_logic_map.md` records current section and paragraph order, paragraph
job, evidence, citations, weakness, and reader question.

`section_blueprints.md` maps target moves for abstract, introduction, related
work, method, experiments/results, discussion, and conclusion as applicable.
Use the technical-paper or benchmark/evaluation skeleton that matches the
claim register and paper type.

`writing_rationale_matrix.md` must use the columns in
`.agents/skills/auto-paper/references/writing-rationale-matrix.md`.

`latex_patch_plan.md` gives patch order, file path, line anchor, risk, guard
command, and compile expectation for each unit.

If `figure_requirement_scan.md` has candidate or planned figures/tables, add
layout units for each accepted figure/table placement. Each unit must specify
the section, visual purpose, claim IDs, citation IDs, caption risk, and whether
the next owner is `$auto-paper-figure`, `$run`, or `USER_GATE`.

For Markdown blogs or reviews, layout must still plan citation placement and
figure/table placement. Do not use `latex_patch_plan.md` as a reason to skip
article structure, citations, or figure planning.

## Gate

Reject shallow rows such as `improve clarity`, `make concise`, or `add
citation` unless they are expanded into reader question, evidence, risk, and
done definition.

## Gate Ledger

Report a Gate ledger entry with commands run, artifacts written, layout-gate
result, any `USER_GATE` or `NOT_RUN` reason, and the next owner before handoff.
