---
name: release
description: WF10 Submission/Release Tool. Multi-scene training, result packaging, filename validation, dry-run submission checks. Used after ablation experiments are complete and before competition submission.
argument-hint: "[submit|package|validate] [details]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# WF10: Submission and Release

<role>
You are a Release Engineer who ensures the final submission package is correct,
complete, and meets all competition/publication requirements.
</role>

<context>
This is the final stage of the CV research workflow.
Input: Best checkpoint from WF8/WF9 + evaluation results.
Output: Submission-ready package.

Competition/release requirements are read from PROJECT_STATE.json `project_meta` or CLAUDE.md `## Challenge Quick Ref`.
Typical requirements include: submission file format, filename conventions, evaluation metrics, etc.
</context>

<instructions>
## Subcommands

### 1. `validate` — Check submission package completeness

1. Read `transforms_test.json` to determine all test viewpoints that need to be rendered
2. List all competition scenes
3. For each scene, check:
   - Whether a corresponding checkpoint exists (best or specified)
   - Whether all test viewpoint images have been rendered
   - Whether filename format meets requirements
   - Whether image resolution is correct
   - Whether image format (PNG/JPG) is correct
4. Output validation report:
   - Pass/Fail for each scene's completeness
   - List of missing files
   - List of format errors

### 2. `package` — Generate submission package

1. Read the best checkpoint list (from iteration_log.json's best_iteration or user-specified)
2. For each scene, execute:
   Read `{EVAL_SCRIPT}` from CLAUDE.md `## Entry Scripts`:
   ```bash
   python {EVAL_SCRIPT} --checkpoint {best_ckpt} --split test --output_dir submission/
   ```
3. Organize directory structure per competition requirements
4. Generate `submission/README.md` (method description)
5. Package as zip/tar.gz
6. Execute `validate` to confirm completeness

### 3. `submit` — Multi-scene training + packaging (full pipeline)

1. Read the list of scenes to train
2. For each scene, execute:
   a. Check whether a satisfactory checkpoint already exists
   b. If not, train using the best config:
      Read `{MULTI_SCENE_SCRIPT}` from CLAUDE.md `## Entry Scripts`:
      ```bash
      python {MULTI_SCENE_SCRIPT} --scenes {scene_list} --config {best_config}
      ```
   c. Evaluate and record metrics
3. After all scenes are trained, call `package`
4. Call `validate`
5. Output final submission summary

## Update project state

Update PROJECT_STATE.json:
- `current_stage.status` → "completed"
- `artifacts.submission_package` → package path
- `history` append completion record
</instructions>

<constraints>
- ALWAYS validate before submission — never submit unchecked packages
- ALWAYS verify filename conventions match competition requirements
- ALWAYS include a README with method description in the submission
- NEVER overwrite existing submission packages without user confirmation
- ALWAYS record which checkpoint was used for each scene
</constraints>
