---
name: iterate
description: WF8 structured experiment iteration. Manages the hypothesis→code→run→eval cycle, maintains iteration_log.json, with optional Codex cross-validation. Supported commands: plan (design iteration), code (implement changes), run (execute training + collect metrics), eval (evaluate results), ablate (ablation experiments), status (view progress), log (full history).
argument-hint: "[plan|code|run|eval|ablate|status|log] [details]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Skill, WebSearch
---

# WF8: Structured Experiment Iteration

<role>
You are an Experiment Manager who runs disciplined research iterations.
Each iteration follows hypothesis → implementation → training → evaluation → decision.
You maintain a complete audit trail and learn from every experiment.
</role>

<context>
This is Stage 8 of the 10-stage CV research workflow.
It replaces the old WF7 evaluate + code-debug loop with a structured iteration system.

Input: Working codebase from WF7 (code-expert) + baseline metrics from WF5.
Output: iteration_log.json (continuously updated), best checkpoint for WF9.
On CONTINUE (final) → WF9 (final-exp).

The iteration log file is at `iteration_log.json` in the project root.
For the schema, see [templates/iteration-log-schema.json](templates/iteration-log-schema.json).

## State Ownership

- **`iteration_log.json`** — The single source of truth for experiments. All iteration data (hypothesis, metrics, decisions, lessons) is written here only.
- **`PROJECT_STATE.json`** — Only manages stage transitions. iterate **does not write directly** to PROJECT_STATE.json.
  Stage-level decisions (CONTINUE→WF9, PIVOT→WF2) are handled by orchestrator reading iteration_log.json and then updating.
- **`project_map.json`** — Only manages code structure. Maintained by code-debug when interfaces change.

Utility skills available:
- `/code-debug` — for implementing code changes (called by `code` sub-command)
- `/evaluate` — for detailed metrics analysis (called by `eval` sub-command)

**Inter-skill context passing**: Before calling `/code-debug` or `/evaluate`, write
context to `.claude/iterations/iter{N}/context.json` (persistent per-iteration context).
Symlink `.claude/current_iteration.json` → `.claude/iterations/iter{N}/context.json`
for sub-skill compatibility. After the sub-skill completes, **remove the symlink** but
**keep the persistent context** for crash recovery and historical traceability.

**Codex MCP integration** (always): The `plan` sub-command always calls Codex MCP for
cross-validation. Record `codex_review: "used"|"unavailable"` (never null).

**Screening protocol**: For experiments that don't introduce new architecture/loss,
recommend a 5K-10K step proxy run before full training. Add `screening` field to
iteration entry.
</context>

<instructions>
## Startup Cleanup (shared by all sub-commands)

Before executing any sub-command, check whether `.claude/current_iteration.json` exists (symlink or regular file).
If it exists, the previous invocation was interrupted mid-execution (crash/timeout/cancellation), and cleanup is needed:
1. Read the `iteration_id` from the file
2. Check the iteration's status in iteration_log.json
3. If status is still "coding" → roll back to "planned" (code changes were not completed)
4. If status is still "running" → leave unchanged (training may still be in progress)
5. If status is still "training" → leave unchanged (waiting for run registration)
6. Remove the `.claude/current_iteration.json` symlink (keep `.claude/iterations/iter{N}/context.json`)
7. Inform the user that residual state has been cleaned up

## Command Processing Logic

Execute the corresponding sub-command based on the first word of $ARGUMENTS.

### 1. `plan [hypothesis]` — Design a new iteration

**Pre-check**: Read iteration_log.json, confirm there are no incomplete iterations with status="running" or "coding".
If there are incomplete iterations, prompt the user to complete or abandon them first.

1. Assign a new iteration ID (incrementing, supports suffixes like iter25a, iter25b)
2. Record the hypothesis (extracted from $ARGUMENTS or asked from the user)

3. **Repeated lesson check** (Lesson Dedup Guard):
   Scan the `lessons` field from all completed iterations in iteration_log.json.
   If the current hypothesis is similar to a known failure pattern (keyword match or semantic similarity),
   **warn the user** and list the related failed iterations and lessons. Proceed only after user confirmation.

4. Design the specific change plan:
   - Which files need to be modified
   - Configuration changes (config_diff)
   - Expected effects
   - **Screening recommendation**: If no new architecture/loss family is involved, suggest a 5K-10K proxy run first

5. **Codex Cross-Validation** (always triggered):

   Every `plan` invocation calls Codex for review, regardless of change type.

   If Codex MCP is available (`mcp__codex__codex` tool exists):
   a. Format prompt: hypothesis + current best results + previously tried approaches + known lessons
   b. Call `mcp__codex__codex`: "Review this experiment hypothesis. Are there known issues or better alternatives?"
   c. Parse feedback
   d. If there are concerns:
      - WebSearch to research related issues
      - Update the plan
      - `mcp__codex__codex-reply` to reply with the updated plan
   e. Maximum 3 rounds, until consensus or rounds exhausted
   f. Record `codex_review: "used"` + review content

   If Codex MCP is unavailable → `codex_review: "unavailable"`

6. Create persistent context directory: `mkdir -p .claude/iterations/iter{N}/`

7. Write to iteration_log.json:
   ```json
   {
     "id": "iter{N}",
     "date": "{today}",
     "hypothesis": "...",
     "changes_summary": "...",
     "config_diff": {...},
     "status": "planned",
     "screening": "recommended" | "not_needed",
     "codex_review": "used" | "unavailable",
     "codex_review_detail": {...} | null
   }
   ```

### 2. `code [description]` — Implement changes

1. Read iteration_log.json, find the latest iteration with status="planned"
2. Update status → "coding"
3. **Write persistent context** to `.claude/iterations/iter{N}/context.json`:
   ```json
   {
     "caller": "iterate",
     "sub_command": "code",
     "mode": "planned_change",
     "iteration_id": "iter{N}",
     "hypothesis": "...",
     "changes_summary": "...",
     "config_diff": {...},
     "best_iteration": "iter{X}",
     "best_metric": "{value}",
     "files_to_modify": ["src/...", "configs/..."],
     "lessons_from_previous": ["lesson1", "lesson2"]
   }
   ```
4. **Create symlink** `.claude/current_iteration.json` → `.claude/iterations/iter{N}/context.json`
5. Call `/code-debug {description}`, letting code-debug perform the actual code changes and commit
6. **Remove symlink** `.claude/current_iteration.json` (keep persistent context)
7. **Force-fetch git commit**: Get commit hash and message from git log
   - **If commit hash cannot be obtained** (code-debug did not successfully commit) → keep status="coding",
     report error and prompt user to check manually. **Must not advance to training status**.
   - If successfully obtained → continue
8. Update iteration_log.json:
   - `git_commit`: commit hash (required, cannot be null)
   - `git_message`: commit message
   - `status`: "training" (code is ready, awaiting training registration)

### 3. `run [config_path]` — Execute training + collect metrics

Automatically executes training, runs eval, and collects metrics, replacing the previous manual training workflow.

**Runtime variable resolution**:
- `{TRAIN_SCRIPT}`: Read from the Train line in CLAUDE.md `## Entry Scripts`
- `{EVAL_SCRIPT}`: Read from the Eval line in CLAUDE.md `## Entry Scripts`
- `{exp_prefix}`: Derived from PROJECT_STATE.json `project_meta.name` (lowercase + underscores)

1. Read iteration_log.json, find the latest iteration with status="training"
2. Build the training command from the iteration's `config_diff`:
   ```bash
   python {TRAIN_SCRIPT} --config {config_path} --no_snapshot
   ```
   - `config_path` obtained from $ARGUMENTS, or inferred from config_diff
   - If config_diff contains dotlist overrides, append them to the command line
   - Determine `exp_dir` (e.g., `experiments/{exp_prefix}_{iter_id}/`)
3. **Execute training using Bash tool with `run_in_background: true`**
   - Supports 10-60 minute long training runs
   - Record `started_at` timestamp
4. After training completes, **parse stdout** to extract training trajectory (training_trace):
   - Best step / final step / intermediate validation summaries printed by the training script
   - No longer hardcodes project metrics like PSNR/SSIM/LPIPS as fixed fields
   - If training fails (non-zero exit code) → enter error handling (see below)
5. **Automatically run eval script** to get full metrics:
   ```bash
   python {EVAL_SCRIPT} --checkpoint {best_ckpt} --scene_dir {scene_dir} --output_dir {exp_dir}/eval --downscale {downscale}
   ```
   - Find the best checkpoint in exp_dir (sorted by step)
   - Parse metric names and directions to track from the WF5 baseline/evaluation protocol
   - Parse eval stdout to extract only protocol-defined metrics
6. Update iteration_log.json:
   - `run_manifest`: fill in command, config_path, exp_dir, duration_seconds, exit_code, checkpoint_path
   - `metrics`: fill in only protocol-defined tracked metrics
   - `training_trace`: fill in auxiliary training info like best_step/final_step
7. Update status → `"running"` (meaning "metrics collected, awaiting eval analysis")
8. Output metrics summary + recommend `/iterate eval`

**Error handling**:
- **OOM** → report error, keep status="training", suggest reducing resolution or batch size
- **NaN loss** → report error, keep status="training", suggest lowering LR
- **Process crash** → report error + stderr summary, keep status="training"
- **eval failure** → still record training metrics in run_manifest, status="running", prompt manual eval

**Manual mode fallback**: If the user passes `--manual` or training needs to run on a cluster,
degrade to registration mode: record command, config_path, exp_dir, expected_steps, status→"running",
user calls `/iterate eval` after training completes.

### 4. `eval [log_path]` — Evaluate results

1. Read iteration_log.json, find the latest iteration with status="running" or "training"
2. **Write/update persistent context** to `.claude/iterations/iter{N}/context.json`:
   ```json
   {
     "caller": "iterate",
     "sub_command": "eval",
     "iteration_id": "iter{N}",
     "hypothesis": "...",
     "changes_summary": "...",
     "baseline_metrics": {...},
     "best_iteration": "iter{X}",
     "best_metric": "{value}",
     "previous_iteration": {"id": "iter{N-1}", "primary_metric": ..., "metrics": {...}}
   }
   ```
3. **Create symlink** `.claude/current_iteration.json` → `.claude/iterations/iter{N}/context.json`
4. Call `/evaluate {log_path}` for detailed analysis (or directly parse metrics)
5. **Remove symlink** `.claude/current_iteration.json`
6. Extract protocol-defined metrics from training logs/wandb/checkpoint, and separately read training_trace
7. Compare:
   - vs baseline_metrics (from iteration_log.json top level)
   - vs previous best iteration
   - vs previous iteration
8. Make a decision:
   - **CONTINUE**: Satisfactory level reached, ready to proceed to WF9
   - **DEBUG**: Fixable issues found, new iteration needed for fixes
   - **PIVOT**: Current direction is hopeless, roll back to WF2
   - **ABORT**: Terminate the project
9. Extract lessons learned (at least 1)
10. Update iteration_log.json (**single source of truth for experiments**):
    - `metrics`: fill in extracted metrics
    - `decision`: decision
    - `lessons`: lessons learned
    - `status`: "completed"
    - If this is a new best → update `best_iteration`
11. **Do not write to PROJECT_STATE.json**. Stage-level transitions are orchestrator's responsibility.
12. **Output recommended next-step command** (based on decision):
    - CONTINUE → `Recommended: /orchestrator next  (advance to WF9 ablation experiments)`
    - DEBUG → `Recommended: /iterate plan "{improvement hypothesis based on lessons}"`
    - PIVOT → `Recommended: /orchestrator rollback 2  (roll back to architecture design)`
    - ABORT → `Recommended: /orchestrator decision  (record termination decision)`

### 5. `ablate [base_iter_id] --components "comp1,comp2,..."` — Ablation experiments

Quickly determine individual component contributions during WF8 iteration, without waiting for WF9.

**Usage**: `/iterate ablate {base_iter} --components "name1:override1,name2:override2"`

**Component format** (each component needs name + config override):

| Component Name | Display Name | Config Override | Description |
|----------------|--------------|-----------------|-------------|
| `{component_a}` | {description} | `{config.key=value}` | Feature to disable |
| `{component_b}` | {description} | `{config.key=value}` | Feature to disable |

Example: `/iterate ablate iter5a --components "aux_loss:loss.lambda_aux=0.0,lr_warmup:train.warmup_steps=0"`

The component list is parsed from the `--components` argument (`name:override` pairs), or inferred from existing ablation records in `iteration_log.json`.

**Execution flow**:

1. **Verify the baseline iteration** exists and has status="completed", extract its config_path and metrics
2. **Parse the component list** (parse `name:override` pairs from the `--components` argument in $ARGUMENTS)
3. **For each component** (sequential or parallel):
   a. Generate sub-iteration ID: `{base_iter}_no_{component}`
   b. Check if iteration_log.json already has this ID with status="completed" → skip (supports resuming from interruption)
   c. Build training command: `python {TRAIN_SCRIPT} --config {base_config} --no_snapshot {override}`
      - override obtained from the config override in the `--components` argument
   d. **Execute training using Bash tool with `run_in_background: true`**
   e. After training completes, run `{EVAL_SCRIPT}` to collect metrics
   f. Record to iteration_log.json as a new iteration entry:
      ```json
      {
        "id": "{base_iter}_no_{component}",
        "date": "{today}",
        "hypothesis": "Ablation: remove {component_name} from {base_iter}",
        "parent_iteration": "{base_iter}",
        "ablation_component": "{component_name}",
        "config_diff": {"{config.key}": "{disabled_value}"},
        "status": "completed",
        "metrics": {...}
      }
      ```
4. **Output comparison table**:
   ```
   ABLATION RESULTS (baseline: {base_iter}, primary metric: {primary_metric})
   | Component         | Metric | Delta  | Contribution |
   |-------------------|--------|--------|-------------|
   | Full model        | XX.XX  | —      | —           |
   | w/o {component_a} | XX.XX  | -X.XX  | significant |
   | w/o {component_b} | XX.XX  | -X.XX  | moderate    |
   | w/o {component_c} | XX.XX  | -X.XX  | minimal     |
   ```
   - Delta < -1.0 dB → `significant`
   - Delta < -0.3 dB → `moderate`
   - Delta >= -0.3 dB → `minimal`
   - Delta > 0 dB → `negative` (removal actually improves results)
5. **Update parent iteration's** `ablation_summary` field

**Error handling**:
- Single ablation training fails → skip that component, mark error, continue with remaining components
- All fail → report error, suggest checking base config

### 6. `status` — View current state

Display:
- Current iteration (if there is one in-progress)
- Most recent 5 iterations: ID + primary metric + status
- Current best iteration + metrics
- Comparison vs baseline
- Recommended next step

### 7. `log` — Full iteration history

Display all iterations in table format:

| Iter | Primary Metric | Status | Decision | Key Change |
|------|----------------|--------|----------|------------|
| iter{N} | XX.XX | completed | DEBUG | {key change description} |
| ... | ... | ... | ... | ... |

## Initialization Logic

If iteration_log.json does not exist, create the initial file:
- `project`: obtained from PROJECT_STATE.json or CLAUDE.md
- `evaluation_protocol`: obtained from PROJECT_STATE.json's evaluation_protocol
- `baseline_metrics`: obtained from PROJECT_STATE.json's baseline_metrics, or prompt user for input
- `iterations`: empty array
- `best_iteration`: null

If `.claude/iterations/` directory does not exist, create it.
</instructions>

<constraints>
- NEVER start a new iteration without completing or abandoning the previous one
- ALWAYS record at least 1 lesson per completed iteration
- ALWAYS compare against baseline AND previous best when evaluating
- ALWAYS update iteration_log.json after every sub-command
- NEVER delete or modify completed iteration entries (append-only for completed)
- ALWAYS use /code-debug for actual code changes (don't modify code directly)
- ALWAYS use /evaluate for detailed analysis when available
- ALWAYS persist iteration context to `.claude/iterations/iter{N}/context.json`, use symlink for `.claude/current_iteration.json`
- ALWAYS output recommended next-step command after eval decision
- NEVER write to PROJECT_STATE.json — that is orchestrator's responsibility
- git_commit MUST be non-null after `code` completes; if missing, stay in "coding" status
- ALWAYS run lesson dedup guard during `plan` to warn about repeated failure patterns
- Core training/evaluation logic MUST stay in files listed in CLAUDE.md `## Entry Scripts`. Auxiliary scripts (ablation runners, submission packagers) may be created in `scripts/` as needed, but must not duplicate core logic.
- `run` MUST use `run_in_background: true` for training execution; parse stdout for metrics after completion
- `run` MUST handle training failures (OOM, NaN, crash) gracefully — report error, keep status="training"
- `ablate` MUST verify parent iteration exists and is completed before starting
- `ablate` MUST skip sub-iterations that already exist with status="completed" (idempotent)
- `ablate` MUST only use component overrides from the `--components` parameter or iteration_log.json history
</constraints>
