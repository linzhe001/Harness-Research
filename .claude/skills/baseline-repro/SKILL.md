---
name: baseline-repro
description: WF5 Baseline Reproduction. Clone comparison method code, adapt to local environment, train and record metrics, output Baseline_Report.md. Used after data preparation and before code planning to provide comparison baselines for the research method.
argument-hint: "[baseline_name or 'all']"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# WF5: Baseline Reproduction

<role>
You are a Reproducibility Engineer who specializes in faithfully reproducing
published ML methods. You ensure fair comparisons by reproducing baselines
under identical data and evaluation conditions.
</role>

<context>
This is Stage 5 of the 10-stage CV research workflow.
Input: Dataset from WF4 + Technical_Spec.md baseline list from WF2.
Output: docs/Baseline_Report.md, updated PROJECT_STATE.json with baseline_metrics, updated project_map.json baselines section.
On success → WF6 (build-plan). On failure → debug reproduction issues or skip problematic baselines.

First, read PROJECT_STATE.json to get project context and Technical_Spec.md for the baseline list.
For the output format, see [templates/baseline-report.md](templates/baseline-report.md).
For language behavior, see [../../shared/language-policy.md](../../shared/language-policy.md).
</context>

<instructions>
1. **Read prerequisite materials**

   - `docs/Technical_Spec.md`: Extract the list of baselines to reproduce (including repo URLs, paper citations)
   - `docs/Dataset_Stats.md` / WF4 output: Data paths and formats
   - PROJECT_STATE.json: Project context
   - If `$ARGUMENTS` specifies a particular baseline name, only reproduce that method

2. **Reproduce baselines one by one**

   Before reproducing each one, first create or confirm the initial runnable environment:
   - Parse dependency files or baseline README
   - Create a conda environment and install necessary dependencies
   - Synchronize the actual environment info into the `## Environment` section of `CLAUDE.md`
   - This environment creation step is part of WF5, and no longer depends on `/env-setup` as a prerequisite in the main workflow

   For each baseline, perform the following steps:

   a. **Obtain code**
      ```bash
      cd baselines/
      git clone {repo_url} {method_name}/  # or use existing submodule
      ```

   b. **Adapt to local environment**
      - Check for dependency conflicts (Python version, CUDA version, PyTorch version)
      - Make minimal modifications to adapt to the local environment (API changes, deprecated interfaces, etc.)
      - Document all adaptation changes

   c. **Train**
      - Use the same configuration as the paper (or the closest available)
      - Follow pre-training rules:
        ```bash
        git add baselines/{method_name}/
        git commit -m "train(baseline/{method_name}): {semantic description}"
        ```
      - Training scripts should integrate git_snapshot (if feasible)

   d. **Evaluate**
      - Use unified evaluation metrics (PSNR / SSIM / LPIPS etc., per project requirements)
      - Evaluate on all relevant scenes
      - Record paper-reported vs reproduced metrics

3. **Comparative analysis**

   - Reproduced metrics vs paper-reported metrics: Is the difference within a reasonable range (±1 dB PSNR)?
   - If the difference is too large, analyze the cause: data differences? training configuration? evaluation method?
   - Determine which baseline serves as the primary comparison target
   - Finalize the evaluation protocol to be used in subsequent WF8: metric names, direction (max/min), primary metric, comparison thresholds

4. **Output report**

   Write to `docs/Baseline_Report.md` (following the [templates/baseline-report.md](templates/baseline-report.md) format), including:
   - Reproduction results table for all baselines
   - Per-baseline adaptation notes and training configurations
   - Discrepancy analysis against paper-reported values

   Preserve the template structure, but localize headings and narrative text according to [../../shared/language-policy.md](../../shared/language-policy.md) unless a field is explicitly marked English-only.

5. **Update project_map.json**

   Update each reproduced baseline node under `baselines/`:
   - `status`: "verified" / "partial" / "failed"
   - `entry_point`: Training entry file

6. **Update project state**

   Update PROJECT_STATE.json:
   - `current_stage.status` → "completed"
   - `artifacts.baseline_report` → "docs/Baseline_Report.md"
   - `baseline_metrics` → Baseline metrics for each scene (for comparison in subsequent /iterate eval)
   - `evaluation_protocol` or equivalent tracked metric definitions → for use by WF8 run/eval
   - `history` append completion record
</instructions>

<constraints>
- ALWAYS commit all baseline adaptations before training (pre-training rule)
- ALWAYS compare reproduced vs paper-reported metrics
- ALWAYS use the same evaluation protocol across all baselines
- NEVER modify baseline code more than necessary — document all changes
- NEVER skip a baseline without recording why it was skipped
</constraints>
