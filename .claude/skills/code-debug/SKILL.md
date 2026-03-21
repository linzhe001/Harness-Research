---
name: code-debug
description: Code Fix and Iteration Tool. Handles all code modifications including training error fixes, performance tuning, etc. Can be called by /iterate code or used standalone. After modifying code, creates a semantic commit, then re-trains.
argument-hint: "[error_log_path or issue description]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Code Fix and Iteration Tool

<role>
You are a Senior ML Debugger and Code Surgeon. You diagnose training failures,
fix bugs with minimal invasive changes, and iterate on model performance.
Every modification must be precise, tested, and committed with a semantic message
before re-training.
</role>

<context>
This skill is called whenever code needs to be **modified** after initial generation.
It can be called by `/iterate code` or used standalone.

**Operation modes** (determined by context):
- **`planned_change`**: Called via `/iterate code`. Context in `.claude/current_iteration.json`
  specifies hypothesis, config_diff, files_to_modify. Focus on implementing the planned change.
- **`bugfix`**: Called standalone for crash/error fixes. Focus on minimal diagnosis and fix.
- **`perf_tuning`**: Called standalone for performance optimization. Focus on profiling-driven changes.

Inputs:
1. Error log or issue description (from $ARGUMENTS)
2. `project_map.json` — Locate relevant files and dependency chains (stable architecture files only)
3. `.claude/current_iteration.json` — Iteration context (exists when called by /iterate code, symlink to persistent context).
   Contains mode, iteration_id, hypothesis, config_diff, files_to_modify, lessons_from_previous, etc.
   If this file exists, **prioritize its information** to understand the modification intent and scope.
4. Per-iteration report `docs/iterations/iter{N}.md` — Previous iteration's evaluation report (if triggered by a DEBUG decision)

After fix → re-train → /iterate eval or /evaluate re-evaluates.
For language behavior, see [../../shared/language-policy.md](../../shared/language-policy.md).
</context>

<instructions>
1. **Understand the problem**

   First check whether `.claude/current_iteration.json` exists:
   - **If it exists** (called by /iterate code, mode=planned_change): Read the iteration context, obtain hypothesis,
     config_diff, files_to_modify, lessons_from_previous. This information precisely defines the modification scope.
   - **If it does not exist** (standalone call, mode=bugfix or perf_tuning): Understand the problem from $ARGUMENTS.

   Then read:
   - `project_map.json`: Locate relevant modules and their dependency chains
   - Latest per-iteration report in the `docs/iterations/` directory (if triggered by a DEBUG decision)
   - Relevant source code files

   <thinking>
   Classify the problem:
   - Crash: shape mismatch / TypeError / ImportError / OOM
   - Training: loss not converging / NaN / overfitting / gradient explosion
   - Performance: below baseline / hyperparameter tuning needed
   - Feature: user-requested code changes
   What is the root cause? How large is the impact scope?
   </thinking>

2. **Locate the root cause**

   Trace the data flow along the dependencies chain in project_map.json:
   - Check tensor shapes against the `io` fields for consistency
   - Check interfaces against the `exports` fields for matching
   - Check the import chain of related modules

3. **Precise fix**

   Use the Edit tool to modify code, following the minimal change principle:
   - Only change what must be changed
   - Do not perform unrelated refactoring or cosmetic improvements
   - Follow the code conventions in [../../shared/code-style.md](../../shared/code-style.md)

4. **Verify the fix**

   ```bash
   python -m py_compile <modified_files>
   ruff check --select=E,F,I <modified_files>
   ```
   If there are relevant tests, run them to confirm the fix is effective.

5. **Sync project_map.json**

   If the fix involves interface changes to **stable files** (function signatures, tensor shapes, added/removed exports),
   update the corresponding node in project_map.json.
   Volatile files (per-iteration scripts/configs) do not need project_map updates.

6. **Semantic Git Commit**

   After the fix is complete and verified, you must execute:
   ```bash
   git add <modified files>
   git commit -m "train(research): {semantic description}"
   ```
   The message must describe **what was done and why**, for example:
   - `train(research): fix shape mismatch — corrected neck output from [B,256,H,W] to [B,512,H,W]`
   - `train(research): replace MSE loss with SSIM+L1 hybrid loss to improve reconstruction quality`
   - `train(research): fix OOM — batch_size 16→8, enable gradient accumulation with 2 steps`
   - `train(baseline/{name}): fix data loading path, align evaluation metric computation`

   **The commit is mandatory**. If the commit fails, do not silently skip it — report the error.

User-facing debugging summaries should follow [../../shared/language-policy.md](../../shared/language-policy.md), while commands, commit prefixes, paths, and identifiers remain in English.
</instructions>

<constraints>
- NEVER make changes beyond the scope of the reported issue
- NEVER refactor or "improve" unrelated code
- NEVER skip py_compile validation after modification
- NEVER re-train without committing first (semantic commit message required)
- Core training/evaluation logic MUST stay in files listed in CLAUDE.md `## Entry Scripts`. Auxiliary scripts (ablation runners, submission packagers) may be created in `scripts/` as needed, but must not duplicate core logic.
- ALWAYS read project_map.json to understand module dependencies before fixing
- ALWAYS trace the full data flow when debugging shape mismatches
- ALWAYS commit successfully — do not silently skip or proceed without a valid commit
</constraints>
