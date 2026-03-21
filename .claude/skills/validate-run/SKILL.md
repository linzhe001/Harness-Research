---
name: validate-run
description: WF7.5 training pipeline validation. Before entering WF8 iteration, first use Codex to review code for baseline equivalence, then run a 100-step smoke test to verify end-to-end pipeline functionality.
argument-hint: "[config_path]"
allowed-tools: Read, Write, Bash, Glob, Grep
---

# WF7.5: Training Pipeline Validation (Code Review + Smoke Test)

<role>
You are a DevOps/ML Engineer and Code Reviewer who validates that the codebase
is correct (vs baseline equivalence) and the training pipeline works end-to-end,
before committing to expensive iteration cycles.
</role>

<context>
This is a gate between WF7 (code generation) and WF8 (iteration).
WF7 writes the full codebase, often by adapting baseline code. Two types of bugs
can slip through:
- **Semantic bugs**: data normalization mismatch, loss sign errors, metric
  computation differences vs baseline — code runs fine but produces wrong results.
- **Infrastructure bugs**: import errors, shape mismatches, OOM — code crashes.

This skill catches both: Codex code review (semantic) + smoke test (infrastructure).
Failure here means issues that must be fixed before entering WF8.

Input: Working codebase from WF7 + config file + baseline code (from baselines/).
Output: Code review findings + smoke test pass/fail report.
On PASS → WF8 (iterate). On FAIL → fix issues via /code-debug.
For language behavior, see [../../shared/language-policy.md](../../shared/language-policy.md).
</context>

<instructions>
1. **Determine configuration and locate files**

   Get config_path from $ARGUMENTS, or infer the default config from CLAUDE.md.
   Read the config file to confirm training parameters.

   Locate three sets of review materials:

   **① WF7 new code** (subject of review):
   - Read all stable module paths from the `src/` node in `project_map.json`
   - Read by responsibility category: model definition (forward pass), data loading (transforms, dataset),
     loss functions, evaluation metric computation (metrics), preprocessing scripts
   - Read the training script `{TRAIN_SCRIPT}` and evaluation script `{EVAL_SCRIPT}` from CLAUDE.md `## Entry Scripts`

   **② Baseline reference code** (equivalence benchmark):
   - Read each baseline's `entry_point` from the `baselines/` node in `project_map.json`
   - Starting from the baseline entry_point, follow the import chain to locate corresponding modules:
     model definition, data loading, loss computation, evaluation metrics, training loop
   - Prefer baselines with `status: verified` as reference

   **③ Design documents** (implementation intent reference):
   - `docs/Technical_Spec.md` (architecture design from WF2, specifying which parts should be equivalent to baseline and which are new additions)

2. **Codex code review** (always attempt)

   WF7.5 is the **only review gate** before code enters iteration, so always attempt Codex review.

   If Codex MCP is available (`mcp__codex__codex` tool exists):

   a. **Collect review materials**: Read the three sets of files located in step 1.
      For each review dimension (data, model, loss, eval), organize the new code and baseline
      corresponding modules **in pairs** for easy side-by-side comparison by Codex.

   b. **Submit review request**, call `mcp__codex__codex`, prompt structure:
      ```
      ## Review Task
      Check equivalence between new code and baseline, answering the review checklist item by item.

      ## New Code (WF7 Implementation)
      ### Data Loading: src/data/...
      {file contents}
      ### Model: src/models/...
      {file contents}
      ### Loss: src/losses/...
      {file contents}
      ### Evaluation: scripts/{EVAL_SCRIPT} + src/utils/metrics.py
      {file contents}
      ### Training Loop: scripts/{TRAIN_SCRIPT}
      {file contents}

      ## Baseline Reference Implementation
      ### Data Loading: baselines/{name}/...
      {file contents}
      ### Model: baselines/{name}/...
      {file contents}
      ### Loss: baselines/{name}/...
      {file contents}
      ### Evaluation: baselines/{name}/...
      {file contents}

      ## Design Intent
      {Key paragraphs from Technical_Spec.md}

      ## Review Checklist (answer each item)
      {see below}
      ```

   c. **Review checklist** (Codex must answer each item):

      **Data pipeline equivalence**:
      - Is image normalization consistent ([0,1] vs [0,255], RGB vs BGR channel order)
      - Is data augmentation (or lack thereof) consistent with baseline
      - Is camera parameter parsing (intrinsics, extrinsics, coordinate system conventions) equivalent
      - Is train/test split logic consistent

      **Model/rendering equivalence**:
      - Is model initialization strategy consistent with baseline (random init, point cloud init, etc.)
      - Is the core computation logic of the forward pass equivalent (preserved baseline portions)
      - Are new modules (e.g., dehazing/enhancement) correctly integrated without breaking gradient flow

      **Loss computation equivalence**:
      - Are shared loss terms with baseline (e.g., L1, SSIM) computed in the same way
      - Are default loss weight values reasonable
      - Can gradients from new loss terms backpropagate correctly

      **Evaluation metric equivalence** (critical, directly affects competition ranking):
      - Is PSNR computation consistent with baseline/competition evaluation (value range, clamping, boundary handling)
      - Are SSIM window size and data_range parameters consistent
      - Is LPIPS network choice (alex vs vgg) consistent with the competition
      - Is output image post-processing (clamping, dtype conversion, save format) consistent with baseline

      **Common ML bug checks**:
      - Are there gradient flow breaks caused by tensor detach
      - Are there in-place operations breaking the autograd graph
      - Is there CPU/GPU device mixing
      - Is the learning rate scheduler step call timing correct

   d. **Parse review results**, classify as:
      - `critical`: will definitely produce incorrect results (e.g., inconsistent metric computation, normalization errors)
      - `warning`: may cause performance differences (e.g., different initialization strategy, loss weight deviations)
      - `info`: style differences, does not affect correctness

   e. If there are critical/warning level concerns:
      - WebSearch to verify related issues (e.g., correct usage of SSIM parameters)
      - `mcp__codex__codex-reply` to reply with verification results, confirming or dismissing concerns
      - Maximum 3 rounds of iteration

   f. Record `codex_review: "used"` + review results

   **If Codex MCP is unavailable**:
   Claude performs a simplified self-review (only checking evaluation metric equivalence and data normalization),
   recording `codex_review: "unavailable"`.

3. **Run 100-step training**

   Read `{TRAIN_SCRIPT}` from CLAUDE.md `## Entry Scripts`:
   ```bash
   python {TRAIN_SCRIPT} --config {config_path} --max_steps 100 --exp_name smoke_test
   ```
   Record:
   - Whether it started successfully (import errors?)
   - Whether it completed 100 steps (crash? OOM? NaN?)
   - Whether loss is in a reasonable range (not NaN, not Inf, shows a decreasing trend)
   - GPU memory usage

4. **Verify checkpoint saving**

   Check whether the smoke test generated checkpoint files:
   - Does the file exist
   - Can it be loaded (`torch.load` does not error)
   - Does it contain required fields (model, optimizer, step, git_commit)

5. **Verify evaluation pipeline**

   Read `{EVAL_SCRIPT}` from CLAUDE.md `## Entry Scripts`:
   ```bash
   python {EVAL_SCRIPT} --checkpoint {smoke_test_checkpoint} --split val
   ```
   Check:
   - Whether evaluation completed
   - Whether metrics are in a reasonable range (PSNR > 5 dB is sufficient; smoke test does not require performance)
   - Whether output images are generated

6. **Verify wandb connection** (if enabled)

   Check whether wandb initialized successfully in the smoke test training logs.

7. **Verify git_snapshot**

   Check whether git_snapshot executed successfully in the smoke test training logs.

8. **Output report**

   Report to the user:

   **Code review results**:
   - Codex review status (used / unavailable)
   - Critical-level findings (if any, list specific differences and suggested fixes)
   - Warning-level findings (list potential risks)
   - Info-level findings (for reference only)

   **Smoke test results**:
   - ✓/✗ 100-step training
   - ✓/✗ Checkpoint save/load
   - ✓/✗ Evaluation pipeline
   - ✓/✗ wandb connection
   - ✓/✗ git_snapshot
   - GPU memory usage

   **Final verdict**:
   - **PASS**: Smoke test all passed AND code review has no critical findings (warnings are recorded but do not block)
   - **REVIEW**: Smoke test passed BUT code review has critical findings — list issues needing confirmation, user decides whether to proceed
   - **FAIL**: Smoke test has failed items — must be fixed

   Keep checklist item names, status labels, commands, and identifiers stable, but localize surrounding narrative text according to [../../shared/language-policy.md](../../shared/language-policy.md) unless a field is explicitly marked English-only.

9. **Cleanup**

   Delete temporary files generated by the smoke test (checkpoints, logs) to avoid polluting the experiment directory.

10. **Update project state**

   If PASS or REVIEW (user confirms to proceed):
   - Update PROJECT_STATE.json: current_stage → WF7.5 completed
   - Append validate_run pass record to history (including code review summary)
   If FAIL or REVIEW (user requests fixes):
   - List failed items + critical review findings
   - Suggest `/code-debug` for fixes
</instructions>

<constraints>
- ALWAYS attempt Codex code review before smoke test (this is the only review gate before WF8)
- ALWAYS run the full validation chain (review → train → checkpoint → eval → wandb → git)
- ALWAYS clean up smoke test artifacts after validation
- NEVER skip any validation step even if previous steps passed
- ALWAYS report specific error messages for any failed step
- Code review critical findings produce REVIEW status, not automatic FAIL — user decides
- ALWAYS check evaluation metric equivalence vs baseline (PSNR/SSIM/LPIPS computation details)
- If Codex unavailable, ALWAYS perform simplified self-review of metric computation and data normalization
</constraints>
