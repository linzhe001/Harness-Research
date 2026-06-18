---
schema_version: "0.1"
page_id: "research_supervision_assets"
title: "Research Supervision Assets"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/research_supervision_assets.md"
source_of_truth: true
status: "current"
summary: "How anonymized research-supervision assets are absorbed into Harness workflow routes without becoming project evidence."
nav:
  section: "detailed_reference"
  position: 45
canonical_sources:
  - path: ".agents/references/research-supervision-patterns.md"
    role: "framework_rule"
  - path: ".agents/references/research-supervision/README.md"
    role: "framework_rule"
  - path: ".agents/references/research-supervision/coverage-matrix.md"
    role: "framework_rule"
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
references:
  - "skill:grill"
  - "skill:change-intake"
  - "skill:build-plan"
  - "skill:iterate"
  - "skill:evaluate"
  - "skill:auto-paper"
  - "term:Conclusion Evidence"
  - "term:Gate Evidence"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/research_supervision_assets.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Research Supervision Assets

## Purpose

This page records how local supervision material was absorbed into Harness.
Runtime workflow should use the internal anonymized assets under
`.agents/references/research-supervision/**` and `.claude/shared/research-supervision/**`,
not `ref/Supervisor-Skills`.

The source PDF and handbook material were converted into Markdown guidance,
ASCII/process diagrams, routing tables, and checklists. Personal names,
affiliations, schools, contact details, logos, speaker identities, screenshots,
raw PDFs, and paper-specific prose were intentionally not imported.

## Model

```text
local supervision material
  -> anonymize and distill
  -> Harness internal assets
  -> Skill Contract required reads
  -> process questions, checklists, paper layouts, figure contracts
  -> current project claims only after Source Artifacts and Evidence Chains exist
```

| Asset | Workflow use |
| --- | --- |
| `research-supervision-patterns.md` | Cross-stage L1 process patterns: pipeline, Grill checks, build/run canvas, paper and figure patterns. |
| `phd-research-primer.md` | Anonymized primer converted from the PDF: research path, direction/problem choice, abstract/intro/method/figure diagrams. |
| `idea-evaluation.md` | `$grill` and `$change`: problem type, fatal flaws, five-axis score, paradigm probes, feasibility gate. |
| `experiment-and-build-canvas.md` | `$build`, `$run`, `$analyze`: smallest verified slice, subtractive MVP, experiment canvas, analysis split. |
| `ai-assisted-research-workflow.md` | Build, figure, and writing work: commander posture, context discipline, AI assistance limits. |
| `paper-writing-layouts.md` | `$write` / `auto-paper-*`: abstract, intro, section blueprint, running example, contribution alignment. |
| `benchmark-evaluation-paper.md` | Benchmark/evaluation papers: RQs, construction pipeline, experiment structure, findings. |
| `scientific-plotting.md` | Figure work: figure roles, contracts, overview/result plots, quality gates. |
| `paper-and-figure-system.md` | Paper skeletons, figure roles, caption claim map, section checks, `RUN_REQUEST` rule. |
| `pre-submission-review.md` | Paper hardening: severity, macro logic, writing details, grammar, LaTeX, figure checks. |
| `case-patterns.md` | Generic story patterns extracted from case studies, without case-specific claims. |
| `coverage-matrix.md` | Maintainer audit only: what was absorbed, anonymized, or intentionally not imported. |

Current route map:

```text
$grill / $change
  -> idea-evaluation + phd-research-primer + research-supervision-patterns

$build / $run / $analyze
  -> experiment-and-build-canvas + ai-assisted-research-workflow

$write / auto-paper-*
  -> paper-writing-layouts + benchmark-evaluation-paper
  -> paper-and-figure-system + scientific-plotting
  -> pre-submission-review + case-patterns

maintainer audit
  -> coverage-matrix
```

## Boundaries

- These assets shape questions, stage plans, figure contracts, and paper
  structure; they are not Conclusion Evidence for any target project.
- They cannot prove dataset access, baseline strength, metric results, method
  novelty, release readiness, or Human Approval.
- They do not authorize downloads, baseline clones, model-weight access,
  Claim Boundary expansion, or stage transitions.
- Any project-specific claim derived from these patterns still needs current
  Source Artifacts, Conclusion Evidence, Gate Evidence, or Approval Evidence.
- `coverage-matrix.md` should remain out of ordinary runtime required reads
  unless the task is maintainer audit or asset integration review.

## Common Confusions

- A supervision pattern can make a better Grill question; it cannot make the
  answer true.
- The anonymized PDF-derived primer is already in
  `phd-research-primer.md`; agents should not reopen or cite the raw PDF during
  normal workflow.
- Example figure assets were abstracted into figure roles and contracts; raw
  images were not copied into Harness assets.
- Case-study material became generic writing patterns; it should not be used as
  factual support for a target paper.
- If a new asset has no Skill Contract route and is not `coverage-matrix.md`,
  treat it as a possible integration gap.

## Related Pages

- [[page:operator_task_index|Operator Action Index]]
- [[page:workflow_layers|Workflow Layers]]
- [[skill:grill]]
- [[skill:change-intake]]
- [[skill:build-plan]]
- [[skill:iterate]]
- [[skill:evaluate]]
- [[skill:auto-paper]]
