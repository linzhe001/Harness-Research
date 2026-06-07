# {project_name}

<!-- Idea: will be filled by /init-project update after WF1 completes -->

## Environment
```bash
# created or confirmed during WF5 baseline-repro
conda activate {env_name or "<pending>"}
```
- Runtime environment will be finalized during WF5 baseline-repro.
- Before WF5, keep this section as a placeholder instead of inventing versions.

## Tech Stack
<!-- will be filled by /init-project update after WF6 completes -->
- GPU: {gpu_name} x{count} ({vram}GB)

### Dataset Paths
<!-- dataset paths will be filled from PROJECT_STATE.json when known -->

## Project Structure
<!-- will be filled by /init-project update after WF7 completes -->

## Core Artifacts
<!-- will be filled by /init-project update after WF7 completes -->
- `MEMORY.md` — Human-readable accepted lessons and decisions once WF10 starts
- `OPERATOR_CONTEXT.md` — Optional operator preferences, not project facts; write only from explicit operator input
- `.evidence/` — Evidence-chain artifacts for compiled current docs when enabled
- `docs/_views/` and `docs/_site/` — Generated evidence-preview data and
  human-readable HTML views; Markdown remains the source of truth.

## Context Layers
- Current fact-layer summaries belong in `docs/20_facts/`.
- `docs/20_facts/Codebase_Map.md` is the operator-facing stable codebase map when present.
- Research Conclusion Evidence tables belong in `docs/30_evidence/`.
- Dynamic protocol drafts belong in `docs/35_protocol/`.
- Human-approved contracts belong in `docs/10_contract/`.
- Current project facts must come from current repo artifacts, logs, configs, metrics, or evidence chains.

## Language Policy
- `interaction_language`: Match the language of the latest substantive user input unless the user explicitly requests another language.
- `artifact_language`: Use the same language as `interaction_language` for natural-language sections in generated docs and reports unless the user asks otherwise.
- Keep file names, paths, commands, code identifiers, JSON/YAML keys, schema fields, workflow IDs, metric keys, and placeholder tokens in English.
- Treat English wording in templates and examples as structural guidance only; localize headings and narrative text unless a field is explicitly marked English-only.

## Entry Scripts
<!-- will be filled by /init-project update after first WF10 experiment -->
<!-- once locked, iteration phase only allows modifying these files; creating new training/eval scripts is prohibited -->

## Global Rule: project_map.json Maintenance
Any skill must sync-update `project_map.json` after creating, deleting, or
renaming stable files, or changing stable interfaces. When
`docs/20_facts/Codebase_Map.md` exists, update it in the same slice.
See `.claude/rules/project-map.md` for detailed rules.

## Global Rule: Code Style
- Before editing `src/`, `scripts/`, `tests/`, durable configs, or supporting utilities, read `.claude/shared/code-style.md` and apply its Pre-Edit Checklist.
- Keep code changes small, readable, and fail-fast; avoid unrelated refactors and broad fallback behavior.
- After Python edits, run `python -m py_compile` and `ruff check --select=E,F,I` on modified files when feasible.

## Global Rule: Ubiquitous Language
- Use `.claude/shared/ubiquitous-language.md` for workflow terms.
- WF6 `/refine-arch` generates `docs/20_facts/Project_Glossary.md`; WF7 `/build-plan` refines it for implementation and creates or refreshes `docs/20_facts/Codebase_Map.md`.
- Distinguish Conclusion Evidence from Gate Evidence; do not use bare `evidence` when the meaning is ambiguous.

## Global Rule: Code Review
- Use `/code-review` for review-only checks of code, git diffs, and code-backed docs.
- Use light mode for targeted understanding, medium mode after code changes, and heavy mode when docs, evidence chains, release claims, or stage gates depend on the code.
- Medium/heavy review reports must include git branch, `HEAD`, base ref or working-tree scope, changed files, changed line ranges, reviewer statuses, reconciled findings, and a Gate ledger.
- Do not edit subject code, current docs, canonical state, or `.evidence/**` during `/code-review`; route ordinary code fixes through `/code-debug` and guardrail fixes through `/harness-maintenance`.

## Global Rule: Documentation Style
- Before writing docs, read `.claude/shared/documentation-evidence-rule.md` and re-read relevant source artifacts from disk.
- For contract, fact, protocol, or release docs, also read `.claude/shared/evidence-chain-rule.md`.
- After durable Markdown docs are finalized, run `/docs-site` to refresh
  `docs/_views/**` and `docs/_site/**`, or report `NOT_RUN`.
- Before implementation, validation, iteration, auto-iteration, or release, read `.claude/shared/contract-gating-rule.md`.
- Before promoting lessons into `MEMORY.md`, read `.claude/shared/lesson-quality-rule.md`.
- Also read `.claude/shared/documentation-style.md`.
- Keep docs concise and human-readable; prefer ASCII flow diagrams for workflows.
- Before refreshing an existing `docs/*.md`, move the old version into `docs/90_legacy/`.

## Workflow
WF0(init) -> WF1(survey) -> WF2(idea-debate) -> WF3(refine-idea) -> WF4(data) -> WF5(baseline) -> WF6(arch) -> WF7(plan) -> WF8(code) -> WF9(validate) -> WF10(iterate) -> WF11(final-exp) -> WF12(release)
WF10 iteration loop: /iterate plan -> /iterate code -> /iterate run -> /iterate eval -> (NEXT_ROUND->repeat | DEBUG->debug round | CONTINUE->WF11 | PIVOT->WF2 idea-debate/refine-idea | ABORT->stop)
After `/grill` exits `grill_draft_ready`, run
`/init-project update-from-grill` to initialize `CLAUDE.md`, `AGENTS.md`, and
`README.md` from candidate Grill context. Do not mark WF1-WF3 complete from
that handoff alone.
Current stage: {current_stage or "not initialized"}

## Custom
<!-- user-added content goes here; preserved during updates -->
