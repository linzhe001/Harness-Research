# AI-Assisted Research Workflow Asset

## Purpose

Use this asset to integrate AI-assisted coding, figure planning, and writing
into Harness without delegating research judgment to the model.

The operator owns the research question, design tradeoffs, evidence judgment,
claim boundaries, and final wording.

## Operating Boundary

AI may accelerate:

- literature organization and checklist construction
- code scaffolding, debugging, refactoring, and test generation
- figure ideation and rough sketches
- grammar, wording, and structure review

AI must not invent:

- research novelty
- citations or reference metadata
- datasets, baselines, metrics, or experimental results
- release claims or paper claims
- approval, reviewer decisions, or ethical clearance

## Commander Pattern

```text
human intent
  -> explicit task contract
  -> AI-generated plan
  -> human/agent check
  -> smallest executable unit
  -> test or review
  -> commit or evidence record
```

Each AI-assisted task should state:

- goal
- inputs and outputs
- constraints
- non-requirements
- first feedback command
- evidence artifact expected

## Build And Debug Discipline

Use small verified units:

```text
plan first
  -> implement one minimum functional unit
  -> run immediate feedback
  -> review behavior
  -> commit or record NOT_RUN
```

Provide error context when asking for fixes:

- failing file
- command
- full traceback or log excerpt
- expected behavior
- actual behavior
- recent changed files

If the third patch does not fix the issue, stop patching and re-plan the debug
hypothesis. Repeated AI patch stacking increases system entropy.

## Context Discipline

Context is the main control surface:

- provide current contracts, roadmap slice, run artifact, and exact files
- keep unrelated ideas out of the prompt
- restart or narrow the session when the model forgets constraints
- prefer stable project docs over memory
- record decisions in the owning Harness artifact instead of relying on chat

## Figure Workflow

AI can discuss visual alternatives, but paper figures need evidence and
editable final assets:

```text
claim or reader question
  -> figure contract
  -> 2-3 layout alternatives
  -> selected sketch
  -> vector redraw or code-generated plot
  -> caption claim audit
```

For quantitative figures, the data source must be a run artifact, metric file,
table, or citation support row. AI-generated images are sketches only.

## Writing Workflow

Use AI for polish after the author has written the logic:

```text
author skeleton
  -> evidence and citation support
  -> AI polish with explicit constraints
  -> sentence-by-sentence verification
  -> banned-pattern and claim-boundary scan
  -> final human-owned prose
```

Do not copy AI-generated paragraphs verbatim into a paper. Treat every AI
sentence as untrusted until checked against local evidence and citations.

## Harness Routing

| Need | Harness route |
|---|---|
| idea pressure test | `grill` or `change` |
| stable code planning | `build` / `build-plan` |
| experiment loop | `run` / `iterate` |
| result interpretation | `analyze` / `evaluate` |
| paper or figure work | `write` / `auto-paper-*` |
| missing experiment from writing | `RUN_REQUEST` back to `run` |

The workflow may reduce friction, but it does not replace Gate Evidence,
Conclusion Evidence, or Human Approval.
