---
schema_version: "0.1"
page_id: "layer_iterate_release"
title: "Iterate And Release Layer"
kind: "concept"
audience: ["operator", "agent", "maintainer"]
source_type: "hand_authored"
source_path: "workflow_handbook/pages/layer_iterate_release.md"
source_of_truth: true
status: "current"
summary: "How WF10-WF12 run iterations, final experiment, and release."
nav:
  section: "details"
  position: 40
canonical_sources:
  - path: "schemas/skill_contracts.json"
    role: "skill_contract"
references:
  - "stage:WF10"
  - "stage:WF11"
  - "stage:WF12"
  - "skill:iterate"
html:
  render: true
  output_path: "docs/_site/workflow_handbook/pages/layer_iterate_release.html"
  preview_index_path: "docs/_views/workflow_handbook_reference_index.json"
---

# Iterate And Release Layer

## Purpose

WF10-WF12 处理多轮实验、final experiment 和 release claim 边界。

## Model

```text
$run
  -> iterate / auto-iterate writes or updates iteration_log.json
  -> $analyze / evaluate interprets artifacts and chooses NEXT_ROUND | DEBUG | CONTINUE | PIVOT | ABORT
  -> $write / auto-paper consumes Experiment Evidence Index and Claim Boundary
  -> RUN_REQUEST routes missing experiment evidence back to $run
  -> WF11 final-exp / WF12 release gates only after evidence and approval are ready
```

## Boundaries

- `iteration_log.json` 是 experiment source of truth。
- `docs/context/experiments.md` 是 WF10 planning、queue、Research Wiki、
  discoveries 和 Assurance Axis 的 canonical working doc；legacy
  `docs/40_iterations/**` 和 `docs/45_discoveries/**` 只是迁移输入。
- `docs/context/memory.md` 保存 promoted lessons；不要把 candidate lesson
  直接写成全局 memory。
- `$run` executes or delegates experiments; `$analyze` turns results into
  decisions; `$write` handles manuscript, release docs, GitHub readiness, and
  scoped release gates.
- `$run` also scans `auto_paper_output/*/run_request_register.{json,md}` so
  paper-discovered missing evidence can become the next WF10 plan.
- `$analyze` should separate verified metric movement, pipeline health,
  explanation candidates, missing controls, claim support, and next experiment.
- `$write` should read detailed paper evidence through
  `docs/30_evidence/Experiment_Evidence_Index.{json,md}` rather than treating
  `iteration_log.json` as sufficient Conclusion Evidence.
- Auto-paper phase order is research, argument, citation, layout, patch,
  harden, with optional response/data/figure branches.
- Final experiment 必须服从 approved contracts 和 Claim Boundary。
- Release claim 不能超出 Human Approval 和 Evidence Chain 支持。

## Common Confusions

- Auto-iterate controller 不替代 Human Approval。
- NEXT_ROUND、DEBUG、CONTINUE、PIVOT、ABORT 是决策词，不是自由文本标签。
- Release readiness 不等于 explicit submit request。
- `RUN_REQUEST` is not a failed paper run; it is a scoped request for `$run` to
  produce missing experiment, ablation, seed, metric, or figure data.

## Related Pages

- [[stage:WF10]]
- [[stage:WF11]]
- [[stage:WF12]]
- [[skill:iterate]]
- [[skill:evaluate]]
- [[skill:auto-paper]]
- [[page:research_supervision_assets|Research Supervision Assets]]
