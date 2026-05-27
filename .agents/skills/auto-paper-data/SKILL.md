---
name: auto-paper-data
description: Run the optional auto-paper data, code, ethics, and reproducibility branch. Use when Codex needs to draft or audit data availability, code availability, ethics boundaries, FAIR metadata, or reproducibility statements for a manuscript.
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
