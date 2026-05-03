# Context Layering Policy

## Purpose

Keep cross-project memory useful without turning it into project fact.

Harness must separate stable process rules, operator preferences, current
project evidence, approved contracts, runtime state, and promoted lessons.

## Layers

Use these layers when loading, writing, or auditing context:

| Layer | Scope | Typical Files | Rule |
|---|---|---|---|
| L1 Core invariants | Cross-project process rules | `.claude/shared/*.md` | Stable, framework-owned, domain-neutral |
| L2 Operator context | User preferences and local working style | `OPERATOR_CONTEXT.md` | May influence defaults; never proves project facts |
| L3 Local/private inputs | Machine config, credentials, local paths | `*.local.*`, `.env.local` | Keep local-only and redact in docs |
| L4 Research evidence | Papers, repos, datasets, benchmarks, metrics | `docs/30_evidence/**` | Evidence only; do not write as rules |
| L5 Dynamic protocol | Current-project protocol draft from evidence | `docs/35_protocol/**` | AI-generated, evidence-backed, reviewable |
| L6 Approved contracts | Human-approved project/eval/claim boundaries | `docs/10_contract/**` | Execution authority after approval |
| L7 Project facts/docs | Current code, data, environment, facts | `docs/20_facts/**`, `CLAUDE.md` | Must come from current artifacts |
| L8 Runtime state/lessons | Iterations, decisions, accepted lessons | `iteration_log.json`, `docs/40_iterations/**`, `docs/50_memory/**`, `MEMORY.md` | Runtime truth and promoted memory |

## Loading Defaults

- Always load L1 before planning, documentation, iteration, or release work.
- Load L2 as preference context only.
- Load L4-L5 during survey, protocol, baseline, drift checks, and release.
- Load L6 before implementation, validation, iteration, auto-iteration, and release.
- Load L7-L8 only when the task needs current facts, run history, or lessons.
- Never load local/private files unless the task is setup or execution and the
  user has granted access to that local context.

## Anti-Contamination Rules

- Do not treat operator preferences as verified project facts.
- Do not turn old project memories into rules for a new project.
- Do not turn research evidence into an approved contract without human review.
- Do not let auto-iteration observations enter `MEMORY.md` directly.
- Do not write project facts from memory; re-read current repo artifacts.
