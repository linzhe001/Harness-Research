---
name: code-debug
description: Code Fix and Iteration Tool for ordinary repository implementation code. Handles training error fixes, planned iteration changes, and performance tuning under src, scripts, configs, project_map, or Codebase_Map. Use /harness-maintenance for hooks, skill contracts, skill routing, and permission policy.
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
This skill is called whenever ordinary implementation code needs to be
**modified** after initial generation.
It can be called by `/iterate code` or used standalone.

Do not use this skill for Harness guardrail maintenance. Route Codex hooks,
skill contracts, skill routing/triggers, `.agents/.claude` skill alignment, and
permission policy changes to `/harness-maintenance`.

**Operation modes** (determined by context):
- **`planned_change`**: Called via `/iterate code`. Context in `.claude/current_iteration.json`
  specifies hypothesis, config_diff, files_to_modify. Focus on implementing the planned change.
- **`bugfix`**: Called standalone for crash/error fixes. Focus on minimal diagnosis and fix.
- **`perf_tuning`**: Called standalone for performance optimization. Focus on profiling-driven changes.

Inputs:
1. Error log or issue description (from $ARGUMENTS)
2. `project_map.json` — Locate relevant files and dependency chains (stable implementation files only)
3. `docs/20_facts/Project_Glossary.md` if it exists — project vocabulary for identifiers, configs, metrics, tests, and errors
4. `docs/20_facts/Codebase_Map.md` if it exists — operator-facing stable codebase map
5. `.claude/current_iteration.json` — Iteration context (exists when called by /iterate code, symlink to persistent context).
   Contains mode, iteration_id, hypothesis, config_diff, files_to_modify, lessons_from_previous, etc.
   If this file exists, **prioritize its information** to understand the modification intent and scope.
6. Per-iteration report `docs/40_iterations/iter{N}.md` — Previous iteration's evaluation report (if triggered by a DEBUG decision; legacy mirror may exist under `docs/iterations/`)
7. `../../shared/sliced-commit-rule.md` — Identify independent Commit Slices before each commit

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
   - `docs/20_facts/Project_Glossary.md` if it exists
   - `docs/20_facts/Codebase_Map.md` if it exists
   - Latest per-iteration report in `docs/40_iterations/`, falling back to legacy `docs/iterations/` if needed (if triggered by a DEBUG decision)
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

   Apply the Pre-Edit Checklist from [../../shared/code-style.md](../../shared/code-style.md) before editing code.

   Use the Edit tool to modify code, following the minimal change principle:
   - Only change what must be changed
   - Do not perform unrelated refactoring or cosmetic improvements
   - Follow the code conventions in [../../shared/code-style.md](../../shared/code-style.md)
   - Preserve project vocabulary from `docs/20_facts/Project_Glossary.md`
   - Keep the fix inside the active slice, bug, or planned iteration scope
   - If the root cause crosses module boundaries, report the boundary issue instead of scattering patches across unrelated modules

4. **Verify the fix**

   ```bash
   python -m py_compile <modified_files>
   ruff check --select=E,F,I <modified_files>
   ```
   If there are relevant tests, run them to confirm the fix is effective.
   Add or update the smallest focused test or smoke command that catches the
   bug or planned behavior when practical; otherwise report the manual feedback
   step and `NOT_RUN` reason.

5. **Sync project_map.json and Codebase_Map.md**

   If the fix involves interface changes to **stable files** (function signatures, tensor shapes, added/removed exports),
   update the corresponding node in project_map.json and update
   `docs/20_facts/Codebase_Map.md` when it exists.
   Volatile files (per-iteration scripts/configs) do not need project_map or
   Codebase_Map updates.
   If `docs/20_facts/Codebase_Map.md` changed, compile its Evidence Chain with
   `python tooling/evidence/compile_doc.py --workspace-root . --doc docs/20_facts/Codebase_Map.md --source project_map.json`
   plus any explicit stable source files needed to support the changed facts,
   or report `compile_doc_or_NOT_RUN`. Do not hand-edit `.evidence/**`.

6. **Sliced Semantic Git Commit**

   After the fix is complete and verified, inspect the diff, identify
   independent Commit Slices, and stage only the files or hunks for the
   completed slice:
   ```bash
   git status --short
   git diff --name-only
   git diff --cached --name-only
   ```

   Commit one completed slice at a time:
   ```bash
   git add <files-or-hunks-for-current-slice>
   git commit -m "train(research): {semantic description}"
   ```
   The message must describe **what was done and why**, for example:
   - `train(research): fix shape mismatch — corrected neck output from [B,256,H,W] to [B,512,H,W]`
   - `train(research): replace MSE loss with SSIM+L1 hybrid loss to improve reconstruction quality`
   - `train(research): fix OOM — batch_size 16→8, enable gradient accumulation with 2 steps`
   - `train(baseline/{name}): fix data loading path, align evaluation metric computation`

   **The commit is mandatory**. If the work contains multiple independent
   slices, commit them separately. If one cross-cutting commit is required,
   record why splitting would be unsafe. If the commit fails, do not silently
   skip it — report the error.

   If `docs/20_facts/Codebase_Map.md` was changed and the fix is otherwise
   validated, invoke `/docs-site` or report `docs_site_boundary_report`. Do
   not render after temporary draft edits.

User-facing debugging summaries should follow [../../shared/language-policy.md](../../shared/language-policy.md), while commands, commit prefixes, paths, and identifiers remain in English.
</instructions>

<constraints>
- NEVER make changes beyond the scope of the reported issue
- NEVER refactor or "improve" unrelated code
- ALWAYS apply the Pre-Edit Checklist in `../../shared/code-style.md` before editing code
- NEVER skip py_compile validation after modification
- NEVER re-train without committing first (semantic commit message required)
- Core training/evaluation logic MUST stay in files listed in CLAUDE.md `## Entry Scripts`. Auxiliary scripts (ablation runners, submission packagers) may be created in `scripts/` as needed, but must not duplicate core logic.
- ALWAYS read project_map.json to understand module dependencies before fixing
- ALWAYS trace the full data flow when debugging shape mismatches
- ALWAYS commit successfully — do not silently skip or proceed without a valid commit
- NEVER bundle unrelated Commit Slices in one commit when they can be separated
</constraints>
