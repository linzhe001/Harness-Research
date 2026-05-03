# {project_name}

<!-- Idea: will be filled by $init-project update after WF1 completes -->

## Environment
```bash
# created or confirmed during WF5 baseline-repro
conda activate {env_name or "<pending>"}
```
- Runtime environment will be finalized during WF5 baseline-repro.
- Before WF5, keep this section as a placeholder instead of inventing versions.

### Dataset Paths
<!-- dataset paths will be filled from PROJECT_STATE.json when known -->

## Tech Stack
<!-- will be filled by $init-project update after WF6 completes -->
- GPU: {gpu_name} x{count} ({vram}GB)

## Project Structure
<!-- will be filled by $init-project update after WF7 completes -->

## Core Artifacts
<!-- will be filled by $init-project update after WF7 completes -->
- `MEMORY.md` — Human-readable append-only lessons and decisions once WF10 starts
- `OPERATOR_CONTEXT.md` — Optional operator preferences, not project facts; write only from explicit operator input
- `.evidence/` — Evidence-chain artifacts for compiled current docs when enabled

## Context Layers
- Current fact-layer summaries belong in `docs/20_facts/`.
- Research evidence belongs in `docs/30_evidence/`.
- Dynamic protocol drafts belong in `docs/35_protocol/`.
- Human-approved contracts belong in `docs/10_contract/`.
- Current project facts must come from current repo artifacts, logs, configs, metrics, or evidence chains.

## Language Policy
- `interaction_language`: Match the language of the latest substantive user input unless the user explicitly requests another language.
- `artifact_language`: Use the same language as `interaction_language` for natural-language sections in generated docs and reports unless the user asks otherwise.
- Keep file names, paths, commands, code identifiers, JSON/YAML keys, schema fields, workflow IDs, metric keys, and placeholder tokens in English.
- Treat English wording in templates and examples as structural guidance only; localize headings and narrative text unless a field is explicitly marked English-only.

## Entry Scripts
<!-- will be filled by $init-project update after first WF10 experiment -->
<!-- once locked, iteration phase only allows modifying these files; creating new training/eval scripts is prohibited -->

## Global Rule: project_map.json Maintenance
Any skill must sync-update `project_map.json` after creating, deleting, or
renaming stable files, or changing stable interfaces.
See `.agents/references/project-map-rule.md` for detailed rules.

## Workflow
WF1(survey) → WF2(idea-debate) → WF3(refine-idea) → WF4(data) → WF5(baseline) → WF6(arch) → WF7(plan) → WF8(code) → WF9(validate) → WF10(iterate) → WF11(final-exp) → WF12(release)
WF10 iteration loop: $iterate plan → $iterate code → $iterate run → $iterate eval → (NEXT_ROUND→repeat | DEBUG→debug round | CONTINUE→WF11 | PIVOT→WF2 idea-debate/refine-idea | ABORT→stop)
Current stage: {current_stage or "not initialized"}

## Documentation Evidence Rule
- Before writing docs, re-read relevant source artifacts from disk.
- Separate verified facts, inferences, and open questions.
- For contract, fact, protocol, or release docs, compile evidence_chain/source_manifest/doc_audit before replacing current Markdown.
- Keep docs concise and human-readable; prefer ASCII flow diagrams for workflows.
- Before refreshing an existing `docs/*.md`, move the old version into `docs/90_legacy/`.

## Custom
<!-- user-added content goes here; preserved during updates -->
