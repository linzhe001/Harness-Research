---
name: build-plan
description: WF7 implementation planning. Translate the WF6 architecture into project file structure, module pseudocode, configuration schema, training pipeline, Implementation_Roadmap.md, project_map.json, and docs/20_facts/Codebase_Map.md.
argument-hint: "[project_path]"
disable-model-invocation: true
allowed-tools: Read, Write, Glob, Grep
---

# WF7: Implementation Roadmap and Project Map

<role>
You are a Software Architect who translates an already selected architecture
into a concrete implementation roadmap. You do not choose the architecture here.
WF6 `/refine-arch` owns architecture decisions; WF7 owns file structure,
implementation order, stable module interfaces, config schemas, tests, and
project_map.json.
</role>

<context>
This is WF7 of the Harness research workflow.
Input: Technical_Spec.md (WF6) + Refined_Idea.md (WF3) + Dataset_Stats.md (WF4) + Baseline_Report.md (WF5) + evaluation contract/protocol.
Output: Implementation_Roadmap.md + project_map.json + `docs/20_facts/Codebase_Map.md` for WF7.
On success → WF8 (code-expert). On failure → return to WF6 or `/deep-check` if a new architecture decision is needed.

First, read PROJECT_STATE.json to locate input artifacts.
For code style requirements, see [../../shared/code-style.md](../../shared/code-style.md).
For the roadmap format, see [templates/implementation-roadmap.md](templates/implementation-roadmap.md).
For the project map schema, see [templates/project-map-schema.json](templates/project-map-schema.json).
For language behavior, see [../../shared/language-policy.md](../../shared/language-policy.md).
For workflow terminology, see [../../shared/ubiquitous-language.md](../../shared/ubiquitous-language.md).
For commit slicing behavior, see [../../shared/sliced-commit-rule.md](../../shared/sliced-commit-rule.md).
WF7 refines `docs/20_facts/Project_Glossary.md` from the approved architecture,
file tree, interfaces, configs, metrics, tests, and error names.
WF7 also creates or refreshes `docs/20_facts/Codebase_Map.md`, the
operator-facing companion to `project_map.json` that summarizes stable
directories, module responsibilities, public interfaces, entry points, and
maintenance owners.
For documentation evidence and anti-hallucination behavior, see [../../shared/documentation-evidence-rule.md](../../shared/documentation-evidence-rule.md).
For documentation style and `docs/90_legacy/` archiving, see [../../shared/documentation-style.md](../../shared/documentation-style.md).
</context>

<instructions>
1. **Read prerequisite materials**
	   - Technical_Spec.md: Architecture design, MVP definition, chosen approach
	   - Refined_Idea.md: task framing, success criteria, and baselines to verify
	   - Dataset_Stats.md: Data statistics
	   - Baseline_Report.md and evaluation protocol/contract
   - Codebase structure: Existing files and modules
   - `docs/20_facts/Project_Glossary.md` if it exists
   - Identify which parts are **main research code** (your innovation) and which are **reproduced baselines** (comparison methods)
   - Update or create `docs/20_facts/Project_Glossary.md` from stable roadmap
     vocabulary; disputed names stay as proposed terms

2. **Design the project file structure**

   Core principle: **Separate main research code from reproduced baselines**.

   Adapt the directory structure based on the project type. The following is a generic template; the actual structure should be customized based on Technical_Spec.md:

   ```
   project_root/
   ├── src/                          # [detailed] Main research code
   │   ├── models/                   # Core models (named per project needs)
   │   ├── data/                     # Data loading and preprocessing
   │   ├── losses/                   # Loss functions
   │   ├── preprocessing/            # Offline preprocessing scripts (optional)
   │   └── utils/                    # Utility functions (including git_snapshot.py)
   ├── baselines/                    # [brief] Reproduced comparison methods
   │   └── {method_name}/            # Each baseline in its own subdirectory
   ├── configs/                      # [medium] Configuration files
   ├── scripts/                      # [medium] Training/evaluation entry scripts
   ├── tests/                        # [brief] Unit tests
   ├── experiments/                  # [minimal] Experiment outputs
   │   ├── logs/
   │   ├── checkpoints/
   │   └── results/
   └── docs/                         # [medium] Documentation
   ```

	   **Key principle**: The directory structure is driven by the architecture design in Technical_Spec.md — do not apply a fixed template and do not introduce new architecture choices here.

3. **Generate project_map.json**

   Generate `project_map.json` (placed in the project root) following the [templates/project-map-schema.json](templates/project-map-schema.json) schema.

   Tiered description strategy:
   - **detailed** — `src/`: List exports, input/output tensor shapes, and module dependencies for each file
   - **medium** — `configs/`, `scripts/`, `docs/`: Purpose and key parameters for each file
   - **brief** — `baselines/`, `tests/`: Baselines only list source/paper/status/entry point; tests only list coverage scope
   - **minimal** — `experiments/`: Only describe directory purpose and storage rules, do not list specific files

   For each baseline subdirectory, must include:
   - `source`: Code source URL
   - `paper`: Paper citation
   - `status`: verified / untested / modified / broken
   - `entry_point`: Training entry file

   Also generate or refresh `docs/20_facts/Codebase_Map.md` from the same
   stable file tree. `project_map.json` remains the machine-readable source;
   `Codebase_Map.md` is the human-readable current fact document and must stay
   synchronized when stable file presence, responsibility, public interface, or
   dependency information changes.

4. **Write module pseudocode and shared interfaces**

   Before broad file planning, convert the WF6 first vertical slice into a
   dependency-ordered slice plan. Each slice must include a `Slice Trace`,
   acceptance checks, feedback command, downstream validation doc, Commit Slice
   boundary, suggested semantic commit message, and out-of-scope work.

   For each **new** file under `src/`, provide:
   - Class/function signatures (with Type Hints)
   - Pseudocode description of core logic
   - Input/output examples (with tensor shapes)
   - Dependency descriptions
   - Required config keys and validation behavior
   - Error conditions and invariants that downstream modules may rely on

   Also define project-level shared interfaces that multiple files must agree
   on, such as dataset item shape, model forward signature, loss inputs,
   metric output schema, checkpoint metadata, and train/eval command contracts.
   These are implementation details of the approved architecture, not new
   architecture choices.

   Preserve the roadmap structure and schema fields, but localize roadmap headings and narrative text according to [../../shared/language-policy.md](../../shared/language-policy.md) unless a field is explicitly marked English-only.

   After `docs/Implementation_Roadmap.md`, `docs/20_facts/Project_Glossary.md`,
   or `docs/20_facts/Codebase_Map.md` is finalized for the stage, invoke
   `/docs-site` or report `docs_site_render_or_NOT_RUN`. Do not render after
   temporary draft edits.

   **Must include pseudocode for `src/utils/git_snapshot.py`**:
   - `git_snapshot(training_type, auto_push)` → dict
   - Responsibilities: Check uncommitted changes, auto-commit (safety net), push, return version info
   - Return fields: commit_hash, commit_message, branch, is_initial, training_type, timestamp

5. **Define configuration schema**

   Define all hyperparameters using dataclass or YAML format:
   - DataConfig: Dataset-related configuration
   - ModelConfig: Model architecture configuration
   - TrainConfig: Training hyperparameters
   - TrackingConfig: wandb tracking configuration (project, entity, tags)
   - ExperimentConfig: Root experiment configuration (contains all sub-configs above)

6. **Design training pipeline**

   Define three stages:
   - Stage 1: Smoke Test — Verify baseline runs on 10% of data
   - Stage 2: Module Integration — Add new modules, verify gradient flow
   - Stage 3: Full Training — Full training, collect metrics

   For each stage, define:
   - Input conditions
   - Execution steps
   - Validation checkpoints (what constitutes a pass)
   - Failure handling

   **Every stage's training script must follow this startup flow**:

   ```
   main():
     1. git_snapshot(training_type) → snapshot    # Version snapshot + push
     2. wandb.init(config, notes=snapshot)        # Experiment tracking
     3. Training loop
     4. Checkpoint saving (includes snapshot.commit_hash)
   ```

   For **baseline training**, training scripts can reuse the same flow,
   just set `training_type` to `"baseline/{method_name}"`.

   Add a test plan for each slice using Red/Green/Refactor when practical, or
   a smoke command plus a `NOT_RUN` reason when automated validation is not
   available. Include a complexity budget for public APIs, new terms,
   dependencies, and maximum files per slice.

7. **Output files**

   Generate two files:

   a. `docs/Implementation_Roadmap.md`, containing:
      - context_summary (≤20 lines)
      - slice_plan and commit_plan, with one Commit Slice per roadmap slice
        unless a cross-cutting reason is recorded
      - module_pseudocode (signatures and pseudocode for each module, including git_snapshot)
      - config_schema (configuration definitions, including TrackingConfig)
      - training_pipeline (three-stage pipeline, including startup flow)
      - validation_checkpoints (checkpoints for each stage)

   b. `project_map.json` (project root), containing the complete tiered file structure description.
      This is the **architectural blueprint** for WF8 code-expert; code-expert must strictly generate code according to this file's structure.

8. **Update project state**

   Update PROJECT_STATE.json:
   - `current_stage.status` → "completed"
   - `artifacts.implementation_roadmap` → file path
   - `artifacts.project_map` → "project_map.json"
   - `history` append completion record
</instructions>

<constraints>
- ALWAYS design for configuration-driven experiments (no hardcoded hyperparameters)
- ALWAYS include a "smoke test" as Stage 1 of the training pipeline
- ALWAYS provide Type Hints in all function signatures
- NEVER design modules longer than 300 lines per file
- NEVER put hyperparameters directly in code
</constraints>
