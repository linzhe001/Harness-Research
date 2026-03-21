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
<!-- will be filled by /init-project update after WF2 completes -->
- GPU: {gpu_name} x{count} ({vram}GB)

### Dataset Paths
<!-- dataset paths will be filled from PROJECT_STATE.json when known -->

## Project Structure
<!-- will be filled by /init-project update after WF6 completes -->

## Core Artifacts
<!-- will be filled by /init-project update after WF6 completes -->

## Entry Scripts
<!-- will be filled by /init-project update after WF7 first experiment -->
<!-- once locked, iteration phase only allows modifying these files; creating new training/eval scripts is prohibited -->

## Global Rule: project_map.json Maintenance
Any skill must sync-update `project_map.json` after **creating, deleting, or renaming** files.
See `.claude/rules/project-map.md` for detailed rules.

## Workflow
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline) → WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
WF8 iteration loop: /iterate plan → /iterate code → /iterate run → /iterate eval → (CONTINUE→WF9 | DEBUG→repeat | PIVOT→WF2)
Current stage: {current_stage or "not initialized"}

## Custom
<!-- user-added content goes here; preserved during updates -->
