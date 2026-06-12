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
- current draft snippets or line anchors

## Required Artifacts

`original_logic_map.md` records current section and paragraph order, paragraph
job, evidence, citations, weakness, and reader question.

`section_blueprints.md` maps target moves for abstract, introduction, related
work, method, experiments/results, discussion, and conclusion as applicable.

`writing_rationale_matrix.md` must use the columns in
`.agents/skills/auto-paper/references/writing-rationale-matrix.md`.

`latex_patch_plan.md` gives patch order, file path, line anchor, risk, guard
command, and compile expectation for each unit.

## Gate

Reject shallow rows such as `improve clarity`, `make concise`, or `add
citation` unless they are expanded into reader question, evidence, risk, and
done definition.

## Gate Ledger

Report a Gate ledger entry with commands run, artifacts written, layout-gate
result, any `USER_GATE` or `NOT_RUN` reason, and the next owner before handoff.
