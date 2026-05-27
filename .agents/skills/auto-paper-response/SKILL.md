---
name: auto-paper-response
description: Run the optional auto-paper reviewer-response branch. Use when Codex needs to handle rebuttal writing, revision response letters, reviewer comment maps, response strategy, or revision commitment registers for an academic manuscript.
---

# Auto Paper Response

## Purpose

Handle reviewer comments and response letters without changing the paper's
claim boundary. This branch is optional and should not be entered by the main
auto-paper loop unless the operator asks for rebuttal or revision-response
work.

## Required Inputs

- reviewer comments or decision letter
- current `claim_register.md`
- current `citation_support_bank.md`
- current patch or revision plan when available
- operator-approved commitments or non-negotiable boundaries

## Outputs

Write under `auto_paper_output/<paper_id>/`:

- `reviewer_comment_map.md`
- `response_strategy.md`
- `revision_commitment_register.md`
- `response_letter.md`

## Rules

- Do not promise experiments, analyses, citations, releases, or revisions that
  are not done or explicitly approved.
- Do not introduce new claims to satisfy reviewers; route new claim pressure to
  argument and citation first.
- Keep response commitments traceable to artifacts, patch ledger rows, or
  operator gates.
- If a reviewer asks for unsupported scope expansion, return `USER_GATE` or
  route to the owning phase instead of writing around the issue.
