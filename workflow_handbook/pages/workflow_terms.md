---
schema_version: "0.1"
page_id: "workflow_terms"
title: "Workflow Terms"
kind: "reference"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/workflow_terms.md"
source_of_truth: true
status: "current"
summary: "Clickable term targets for handbook references."
nav:
  section: "reference"
  position: 50
canonical_sources:
  - path: ".agents/references/ubiquitous-language.md"
    role: "framework_rule"
references:
  - "term:Entrypoint"
  - "term:Visible Skill Alias"
  - "term:Stage"
  - "term:Skill"
  - "term:Gate Evidence"
  - "term:Pending Request"
  - "term:Human Approval"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/workflow_terms.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Workflow Terms

## Source Of Truth

Canonical definitions live in `.agents/references/ubiquitous-language.md`. This page provides stable HTML anchors for handbook links.

## Fields Or Paths

### Entrypoint

A human-facing visible alias used to start workflow work. Current Entrypoints
are `$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, and
`$change`. Internal runtime names such as `workflow-supervisor`, `iterate`,
`evaluate`, `auto-paper`, and `change-intake` are route targets or detailed
references, not extra first-layer entrypoints.

### Visible Skill Alias

A small `$` / `/` command surface that routes to an internal runtime or Skill
Contract source without creating a new Skill Contract. Current visible aliases
are `grill`, `prepare`, `build`, `run`, `analyze`, `write`, and `change`.
Internal skill sources remain readable by path and may be selected by hook
route hints, but they should not appear in autocomplete.

### Stage

A named internal workflow phase such as WF5, WF10, or release. Use detailed
reference pages for artifact and gate inspection, not as the normal first user
entrypoint.

### Skill

An agent behavior contract for a stage or bounded task.

### Skill Contract

The machine-readable rule set in `schemas/skill_contracts.json`.

### Gate Evidence

Proof that a command, test, review, approval check, or workflow gate was attempted and what it returned.

### Gate Ledger

A command/result/reason/artifact report.

### Automation Policy

Grill-scoped operator decision that defines which later non-Grill flows may
auto-proceed, plus budgets, forbidden directions, external access limits, and
stop conditions.

### Claim Delta Evidence

Gate Evidence and Conclusion Evidence that record how a paper claim, release
claim, or claim boundary changed, which Source Artifacts support the change,
and why the change stays inside the active Automation Policy.

### Experiment Queue

Prioritized queue of pending experiment questions, falsifiers, assurance gaps,
and run requests that WF10 planning consumes.

### Research Wiki

Mutable researcher-facing index of observations, phenomena, methods, open
questions, and accepted findings, backed by Source Artifacts and distinct from
Approved Contracts.

### Conclusion Evidence

Traceable support from Source Artifacts to a Claim.

### Evidence Chain

Structured source-to-claim support relation.

### Human Approval

Explicit operator approval in the current conversation or auditable artifact.

### Review Packet

Human decision input. It is not approval.

### Pending Request

A typed supervisor-owned request for human input, approval, steering, review
edit, or escalation.

## Validation

If a term changes, update `.agents/references/ubiquitous-language.md`, rebuild the reference index, and rerender the handbook site.

## Related References

- [[term:Entrypoint]]
- [[term:Visible Skill Alias]]
- [[term:Stage]]
- [[term:Skill]]
- [[term:Gate Evidence]]
- [[term:Pending Request]]
- [[term:Human Approval]]
