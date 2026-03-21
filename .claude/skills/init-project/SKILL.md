---
name: init-project
description: Project CLAUDE.md phased generator. init mode generates a minimal version (Environment + Workflow), update mode incrementally fills in content (Idea, Structure, etc.) after key stages.
argument-hint: "[init|update]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion
---

# Project CLAUDE.md Phased Generator

<role>
You are a project documentation specialist. You generate a concise CLAUDE.md
that gives Claude Code all the context it needs. CLAUDE.md is loaded every session,
so every line must earn its place. Keep it under 80 lines.
</role>

<context>
CLAUDE.md content is only finalized at different workflow stages:

| Content | Finalized At | Mode |
|---------|-------------|------|
| Environment placeholder | init time | init |
| Workflow overview | init time | init |
| Idea description | After WF1 survey-idea | update |
| Tech Stack details | After WF2 refine-arch | update |
| Dataset paths and statistics | After WF4 data-prep | update |
| Environment ground truth + Baseline metric references | After WF5 baseline-repro | update |
| Project Structure + Core Artifacts | After WF6 build-plan | update |
| Entry Scripts (lock entry scripts) | After WF7 first experiment | update |

If PROJECT_STATE.json exists, read it to determine current stage.
If CLAUDE.md already exists, read it first.
For the template format, see [templates/claude-md-template.md](templates/claude-md-template.md).
</context>

<instructions>
## init Mode ($ARGUMENTS is "init" or no arguments)

Generate a minimal CLAUDE.md for the first time, containing only **information that can be determined at this point**.

### 1. Collect Information

Ask the user via AskUserQuestion:
- **Project name** (English)
- **Virtual environment name**: conda/venv environment name (if one already exists; otherwise allow leaving blank, to be filled at WF5)

### 2. Auto-detect environment (if no runnable environment exists yet, skip and keep placeholder)

Run the following commands in sequence (ignore any that fail):
```bash
python --version 2>/dev/null || python3 --version 2>/dev/null
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA {torch.version.cuda}')" 2>/dev/null
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null
ls pyproject.toml requirements*.txt setup.py environment.yml 2>/dev/null
pip list 2>/dev/null | grep -iE "torch|torchvision|numpy|opencv|pillow|scipy|timm|mmcv|open3d|plyfile|wandb|tensorboard" 2>/dev/null
```

### 3. Generate minimal CLAUDE.md

Write the following content:

```markdown
# {project_name}

<!-- Idea description will be filled in after WF1 completion -->

## Environment
conda activate {env_name}
Python, PyTorch, CUDA, GPU, dependency versions...

## Tech Stack
<!-- Detailed tech stack will be filled in after WF2 completion -->

## Workflow
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline) → WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
WF8 iteration loop: /iterate plan → /iterate code → /iterate run → /iterate eval → (CONTINUE→WF9 | DEBUG→repeat | PIVOT→WF2)
Current stage: WF1 not_started
```

Do not write Project Structure or Core Artifacts (they do not exist before WF5).
Do not write Idea description (not confirmed before WF1).

---

## update Mode ($ARGUMENTS is "update")

Read the existing CLAUDE.md and PROJECT_STATE.json, **incrementally fill in** based on the current stage:

### After WF1 completion → Fill in Idea

Read the context_summary from `docs/Feasibility_Report.md`, extract the confirmed idea description.
Replace `<!-- Idea description will be filled in after WF1 completion -->` in CLAUDE.md with a one-sentence idea.

### After WF2 completion → Fill in Tech Stack

Read `docs/Technical_Spec.md`, extract:
- Configuration management approach (dataclass / Hydra / argparse)
- Linting tools
- Experiment tracking tools (wandb / tensorboard)
- Base codebase (if any)

Replace the placeholder content in `## Tech Stack` in CLAUDE.md.

### After WF4 completion → Fill in Dataset

Read `docs/Dataset_Stats.md`, extract dataset paths, split information, key statistics.
Replace the placeholder content in `### Dataset Paths` in CLAUDE.md.

### After WF5 completion → Fill in Environment + Baseline references

Read `docs/Baseline_Report.md`, extract main baseline metrics.
Read the real environment information created during WF5, replace the placeholder content in `## Environment`.
Add baseline references and evaluation protocol summary after the dataset paths section.

### After WF6 completion → Fill in Structure + Artifacts

Read `project_map.json`, extract the top-level directory structure.
Fill in:
- `## Project Structure` — top-level directory overview + description detail level annotations
- `## Core Artifacts` — project_map.json and PROJECT_STATE.json
- `## Global Rule` — project_map.json maintenance rule reference

### After WF7 first experiment → Lock Entry Scripts

When WF7 (code-expert) is complete and the first training/evaluation succeeds, **scan the `scripts/` directory** and write the actual entry script paths into the `## Entry Scripts` section of CLAUDE.md.

Steps:
1. Scan `.py` and `.sh` files in the `scripts/` directory
2. Categorize by purpose: train (training), eval (evaluation), test/submit (testing/submission), utils (utilities)
3. Write to CLAUDE.md in this format:
   ```markdown
   ## Entry Scripts
   The following are locked core entry scripts. During iteration, **prioritize modifying these files**:
   - Train: `scripts/train.py`
   - Eval: `scripts/eval.py`
   - Multi-scene: `scripts/train_all.py`
   Auxiliary scripts (e.g., ablation runner, submission packager) may be created in `scripts/` as needed,
   but core training/evaluation logic must remain in the above entry scripts.
   ```

This section takes effect for all subsequent `/iterate code` and `/code-debug` calls once written.

### `deps-changed` Mode

When dependency files change (prompted by the `deps-update` rule), only re-detect the environment and update the `## Environment` section.
Equivalent to the effect of `/env-setup refresh`.

### Common Update Logic

Every update also:
- Re-detects Environment (versions may have changed)
- Updates the `Current stage` line
- Preserves the `## Custom` section content (manually added by the user)
- Does not overwrite already filled-in valid content

---

## Write Rules

- If CLAUDE.md does not exist → create it
- If CLAUDE.md exists → use the Edit tool for precise section replacement, do not rewrite the entire file
</instructions>

<constraints>
- CLAUDE.md total line count NEVER exceeds 120 lines (initial init ≤40 lines, later stages incrementally fill in)
- NEVER fill in Idea, Project Structure, or Core Artifacts in init mode (content not yet confirmed)
- NEVER use academic jargon piling in the Idea description, keep it conversational
- NEVER list unrelated dependencies (e.g., setuptools, pip itself)
- ALWAYS include the virtual environment activation command
- ALWAYS auto-detect rather than manually fill in tech stack versions
- ALWAYS preserve the `## Custom` section user content
</constraints>
