# Detailed Workflow Stage Reference

本文件由 `schemas/skill_contracts.json` 生成，是 detailed reference，不是
operator 的第一层入口。日常操作先从 visible aliases 选择：
`$grill`, `$prepare`, `$build`, `$run`, `$analyze`, `$write`, `$change`。
内部 Skill Contract 仍然存在，但它们是 detailed reference，
不是 autocomplete 入口。

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

一句话: Initialize or refresh compact workspace guidance and workflow state.

怎么启动: After `$grill` reaches `grill_draft_ready`, run the internal `init-project update-from-grill` mode. For framework setup, use `AI_AGENT_SETUP.md`.

完成后得到: `AGENTS.md`, `CLAUDE.md`, and optional README guidance are refreshed from candidate Grill context without inventing workflow completion.

深入阅读: [[stage:WF0|WF0 details]], [[skill:init-project|init-project Skill]]

### WF1 Survey Idea

一句话: Collect early Conclusion Evidence and decide whether the idea is worth pursuing.

怎么启动: `$grill` when the idea still needs evidence-backed clarification.

完成后得到: `docs/Feasibility_Report.md` and evidence tables summarize viability and open questions.

深入阅读: [[stage:WF1|WF1 details]], [[skill:survey-idea|survey-idea Skill]]

### WF2 Idea Debate

一句话: Compare candidate directions and choose the strongest research path.

怎么启动: `$grill` to compare candidate directions and expose tradeoffs.

完成后得到: `docs/Idea_Debate.md` records the selected direction, alternatives, and risks.

深入阅读: [[stage:WF2|WF2 details]], [[skill:idea-debate|idea-debate Skill]]

### WF3 Refine Idea

一句话: Turn the selected idea into a tighter research question and execution target.

怎么启动: `$grill` until the selected direction is executable enough for prepare.

完成后得到: `docs/Refined_Idea.md` defines scope, hypothesis, and known unknowns.

深入阅读: [[stage:WF3|WF3 details]], [[skill:refine-idea|refine-idea Skill]]

### WF4 Data Prep

一句话: Make data facts explicit before baseline or architecture work starts.

怎么启动: `$prepare` after Grill readiness records dataset sources and targets.

完成后得到: Dataset stats, data facts, configs, and evidence tables are current.

深入阅读: [[stage:WF4|WF4 details]], [[skill:data-prep|data-prep Skill]]

## Contract & Plan

WF5-WF7: establish baseline, approved boundaries, architecture, and slices.

### WF5 Baseline Repro

一句话: Reproduce or establish a baseline and prepare approval-facing contracts.

怎么启动: `$prepare` after executable baseline source provenance is approved.

完成后得到: Baseline report, baseline evidence, and draft or approved contracts are ready for later gates.

深入阅读: [[stage:WF5|WF5 details]], [[skill:baseline-repro|baseline-repro Skill]]

### WF6 Refine Arch

一句话: Refine the technical architecture within approved boundaries.

怎么启动: `$build` after prepare has data/baseline facts and boundaries.

完成后得到: `docs/Technical_Spec.md` and glossary updates define the implementation shape.

深入阅读: [[stage:WF6|WF6 details]], [[skill:refine-arch|refine-arch Skill]]

### WF7 Build Plan

一句话: Convert the architecture into bounded implementation slices.

怎么启动: `$build` after architecture intent is stable enough to slice.

完成后得到: `docs/Implementation_Roadmap.md`, `project_map.json`, and codebase map guidance align.

深入阅读: [[stage:WF7|WF7 details]], [[skill:build-plan|build-plan Skill]]

## Build & Validate

WF8-WF9: implement a bounded slice and validate it with Gate Evidence.

### WF8 Code Expert

一句话: Implement one bounded code slice under the current plan.

怎么启动: `$build` for first-pass implementation, or `$change` for later code deltas.

完成后得到: Changed code, focused validation, and map updates are ready for review.

深入阅读: [[stage:WF8|WF8 details]], [[skill:code-expert|code-expert Skill]]

### WF9 Validate Run

一句话: Validate the implementation before structured iteration.

怎么启动: `$build` continues through validate-run postconditions.

完成后得到: `docs/Validate_Run_Report.md` records PASS, REVIEW, or FAIL with Gate Evidence.

深入阅读: [[stage:WF9|WF9 details]], [[skill:validate-run|validate-run Skill]]

## Iterate & Release

WF10-WF12: run iterations, final experiment checks, and release packaging.

### WF10 Iterate

一句话: Run the Ralph-style loop: plan, code, run, evaluate, and decide the next round.

怎么启动: `$run` for experiment execution and `$analyze` for result decisions.

完成后得到: `iteration_log.json`, `docs/context/experiments.md`, and `docs/context/memory.md` capture runs, lessons, and decisions.

深入阅读: [[stage:WF10|WF10 details]], [[skill:iterate|iterate Skill]]

### WF11 Final Exp

一句话: Run final experiment checks against approved contracts and claim boundaries.

怎么启动: `$run` for final experiments and `$analyze` for final interpretation.

完成后得到: `docs/Final_Experiment_Matrix.md` records the final experiment plan and gate result.

深入阅读: [[stage:WF11|WF11 details]], [[skill:final-exp|final-exp Skill]]

### WF12 Release

一句话: Prepare release artifacts while keeping claims inside the approved boundary.

怎么启动: `$write` for paper, release docs, GitHub readiness, and scoped release gates.

完成后得到: `submission/**`, release docs, and final Gate Evidence are ready for explicit submit approval.

深入阅读: [[stage:WF12|WF12 details]], [[skill:release|release Skill]]
