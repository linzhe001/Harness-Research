---
name: auto-paper-data
description: "Internal Harness instruction source for auto-paper-data. Route through visible Harness aliases or hook contracts instead of invoking directly."
---

# Auto Paper Data

## Purpose

Prepare availability and reproducibility statements from verified project
facts. This branch does not invent dataset access, license state, ethics
approval, code release status, compute details, or artifact permanence.

## Required Inputs

- project data locations and release policy
- code repository or package status when known
- license, embargo, or access restrictions
- ethics, consent, IRB, or human-subject boundaries when applicable
- reproducibility materials such as configs, seeds, checkpoints, and commands

## Outputs

Write under `auto_paper_output/<paper_id>/`:

- `data_availability_statement.md`
- `code_availability_statement.md`
- `reproducibility_checklist.md`
- `ethics_boundary.md`

## Rules

- If availability, licensing, ethics, or release status is unclear, write a
  `USER_GATE` item instead of filling a plausible statement.
- Separate current verified facts from planned future releases.
- Do not state that data or code is public unless the artifact or operator
  approval proves it.
- Route new evidence claims back to argument, citation, or harden.

## Gate Ledger

Report a Gate ledger entry with commands run, artifacts written, unresolved
availability or ethics facts, any `USER_GATE` or `NOT_RUN` reason, and the next
owner before handoff.
