---
name: auto-paper-layout
description: Run the auto-paper layout phase. Use to map current TeX logic, design section and paragraph blueprints, create a writing rationale matrix, citation plan, and LaTeX patch plan before any manuscript edits.
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
