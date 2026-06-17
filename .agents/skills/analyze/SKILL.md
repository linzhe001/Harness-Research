---
name: analyze
description: "Visible Harness analyze entry. Use after experiment runs to turn results into interpretation, decisions, and next-run or writing guidance."
---

# Analyze

Use `$analyze` as the human-facing alias for result analysis. This is not a
separate Skill Contract.

Read and follow:
- `../../../.agents/skills/evaluate/SKILL.md`
- `../../../.agents/references/workflow-guide.md`
- `../../../AGENTS.md`
- `../../../CLAUDE.md`

Analyze current run artifacts and iteration logs, then produce decision-ready
insights that guide the next `$run`, a `$grill` pivot, or `$write`.

After updating completed run evidence, refresh
`docs/30_evidence/Experiment_Evidence_Index.{json,md}` using
`tooling/evidence/build_experiment_evidence_index.py` so `$write` can consume
experiment results without treating `iteration_log.json` as the sole source of
truth. If not run, report `NOT_RUN` with the reason.
