# Detailed Workflow Stage Reference

本文件由 `schemas/skill_contracts.json` 生成，是 detailed reference，不是
operator 的第一层入口。日常操作先从 Grill 或 Execution Supervisor
选择顶层入口；`prepare/build/iterate/release/change` 是 supervisor actions。

只有当你需要追踪内部 WF artifact、定位某个 Skill Contract、或排查
Gate/postcondition 失败时，才使用本页。完整推荐读取、声明路径、
artifact 输出和 Gate 条件保留在 Stage / Skill 详情页。

生成命令:

```bash
python tooling/codex_hooks/generate_stage_cards.py --workspace-root . --output workflow_handbook/Workflow_Stage_Cards.md
```

详细排查时的读法:

```text
Stage -> 一句话 -> 怎么启动 -> 完成后得到 -> 深入阅读
```

## Explore

WF0-WF4: turn an initial idea into scoped direction and data facts.

### WF0 Init

一句话: Initialize or refresh the workspace guidance and workflow state.

怎么启动: `$init-project` for guidance setup, or `$orchestrator` for state checks.

完成后得到: `AGENTS.md`, `CLAUDE.md`, `PROJECT_STATE.json`, and optional scaffold are ready.

深入阅读: [[stage:WF0|WF0 details]], [[skill:init-project|init-project Skill]]

### WF1 Survey Idea

一句话: Collect early Conclusion Evidence and decide whether the idea is worth pursuing.

怎么启动: `$survey-idea` with the research idea and constraints.

完成后得到: `docs/Feasibility_Report.md` and evidence tables summarize viability and open questions.

深入阅读: [[stage:WF1|WF1 details]], [[skill:survey-idea|survey-idea Skill]]

### WF2 Idea Debate

一句话: Compare candidate directions and choose the strongest research path.

怎么启动: `$idea-debate` after WF1 has enough evidence to compare options.

完成后得到: `docs/Idea_Debate.md` records the selected direction, alternatives, and risks.

深入阅读: [[stage:WF2|WF2 details]], [[skill:idea-debate|idea-debate Skill]]

### WF3 Refine Idea

一句话: Turn the selected idea into a tighter research question and execution target.

怎么启动: `$refine-idea` with the selected direction and unresolved assumptions.

完成后得到: `docs/Refined_Idea.md` defines scope, hypothesis, and known unknowns.

深入阅读: [[stage:WF3|WF3 details]], [[skill:refine-idea|refine-idea Skill]]

### WF4 Data Prep

一句话: Make data facts explicit before baseline or architecture work starts.

怎么启动: `$data-prep` after the dataset path and intended evaluation surface are known.

完成后得到: Dataset stats, data facts, configs, and evidence tables are current.

深入阅读: [[stage:WF4|WF4 details]], [[skill:data-prep|data-prep Skill]]

## Contract & Plan

WF5-WF7: establish baseline, approved boundaries, architecture, and slices.

### WF5 Baseline Repro

一句话: Reproduce or establish a baseline and prepare approval-facing contracts.

怎么启动: `$baseline-repro` after data facts and baseline target are clear.

完成后得到: Baseline report, baseline evidence, and draft or approved contracts are ready for later gates.

深入阅读: [[stage:WF5|WF5 details]], [[skill:baseline-repro|baseline-repro Skill]]

### WF6 Refine Arch

一句话: Refine the technical architecture within approved boundaries.

怎么启动: `$refine-arch` after baseline and contract boundaries are available.

完成后得到: `docs/Technical_Spec.md` and glossary updates define the implementation shape.

深入阅读: [[stage:WF6|WF6 details]], [[skill:refine-arch|refine-arch Skill]]

### WF7 Build Plan

一句话: Convert the architecture into bounded implementation slices.

怎么启动: `$build-plan` after the technical spec is stable enough to slice.

完成后得到: `docs/Implementation_Roadmap.md`, `project_map.json`, and codebase map guidance align.

深入阅读: [[stage:WF7|WF7 details]], [[skill:build-plan|build-plan Skill]]

## Build & Validate

WF8-WF9: implement a bounded slice and validate it with Gate Evidence.

### WF8 Code Expert

一句话: Implement one bounded code slice under the current plan.

怎么启动: `$code-expert` for first-pass planned work, or `$code-debug` for fixes.

完成后得到: Changed code, focused validation, and map updates are ready for review.

深入阅读: [[stage:WF8|WF8 details]], [[skill:code-expert|code-expert Skill]]

### WF9 Validate Run

一句话: Validate the implementation before structured iteration.

怎么启动: `$validate-run` with the acceptance commands and expected behavior.

完成后得到: `docs/Validate_Run_Report.md` records PASS, REVIEW, or FAIL with Gate Evidence.

深入阅读: [[stage:WF9|WF9 details]], [[skill:validate-run|validate-run Skill]]

## Iterate & Release

WF10-WF12: run iterations, final experiment checks, and release packaging.

### WF10 Iterate

一句话: Run the Ralph-style loop: plan, code, run, evaluate, and decide the next round.

怎么启动: `$iterate plan`, `$iterate run`, and `$iterate eval`.

完成后得到: `iteration_log.json` and `docs/40_iterations/**` capture runs, lessons, and decisions.

深入阅读: [[stage:WF10|WF10 details]], [[skill:iterate|iterate Skill]]

### WF11 Final Exp

一句话: Run final experiment checks against approved contracts and claim boundaries.

怎么启动: `$final-exp` after WF10 evidence supports a final evaluation.

完成后得到: `docs/Final_Experiment_Matrix.md` records the final experiment plan and gate result.

深入阅读: [[stage:WF11|WF11 details]], [[skill:final-exp|final-exp Skill]]

### WF12 Release

一句话: Prepare release artifacts while keeping claims inside the approved boundary.

怎么启动: `$release` after WF11 and release readiness gates are satisfied.

完成后得到: `submission/**`, release docs, and final Gate Evidence are ready for explicit submit approval.

深入阅读: [[stage:WF12|WF12 details]], [[skill:release|release Skill]]
