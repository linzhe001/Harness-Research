# {project_name}

<!-- Idea: 将在 WF1 完成后由 /init-project update 填入 -->

## Environment
```bash
# created or confirmed during WF5 baseline-repro
conda activate {env_name or "<pending>"}
```
- Runtime environment will be finalized during WF5 baseline-repro.
- Before WF5, keep this section as a placeholder instead of inventing versions.

## Tech Stack
<!-- 将在 WF2 完成后由 /init-project update 填入 -->
- GPU: {gpu_name} x{count} ({vram}GB)

### Dataset Paths
<!-- dataset paths will be filled from PROJECT_STATE.json when known -->

## Project Structure
<!-- 将在 WF6 完成后由 /init-project update 填入 -->

## Core Artifacts
<!-- 将在 WF6 完成后由 /init-project update 填入 -->

## Entry Scripts
<!-- 将在 WF7 完成首次实验后由 /init-project update 填入 -->
<!-- 锁定后，迭代阶段只允许修改这些文件，禁止新建训练/评估脚本 -->

## Global Rule: project_map.json 维护
任何 skill 在**创建、删除或重命名**文件后，必须同步更新 `project_map.json`。
详细规则见 `.claude/rules/project-map.md`。

## Workflow
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline) → WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
WF8 迭代循环: /iterate plan → /iterate code → /iterate run → /iterate eval → (CONTINUE→WF9 | DEBUG→repeat | PIVOT→WF2)
Current stage: {current_stage or "not initialized"}

## Custom
<!-- 用户手动添加的内容放在这里，update 时会保留 -->
