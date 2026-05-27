# Auto-Paper Loop

## Phase Sequence

The auto-paper loop is a writing workflow with six ordered phases:

```text
research -> argument -> citation -> layout -> patch -> harden
```

Each phase has one owning branch skill. The orchestrator can call a branch
directly only when the required upstream artifacts exist or the branch is
explicitly responsible for creating them.

| phase | owner | required purpose |
| --- | --- | --- |
| `research` | `$auto-paper-research` | Build source, draft, reference, and style context. |
| `argument` | `$auto-paper-argument` | Fix central tension, evidence-backed claims, and boundaries. |
| `citation` | `$auto-paper-citation` | Map claims to support grades and citation keys. |
| `layout` | `$auto-paper-layout` | Produce paragraph/unit plans before any LaTeX edit. |
| `patch` | `$auto-paper-patch` | Apply bounded LaTeX changes from the patch plan. |
| `harden` | `$auto-paper-harden` | Audit artifact chain, claim support, LaTeX, and reviewer risk. |

## Decisions

Use these machine-readable decisions in phase summaries and controller output:

- `NEXT_UNIT`
- `REWORK_RESEARCH`
- `REWORK_ARGUMENT`
- `REWORK_CITATION`
- `REWORK_LAYOUT`
- `REWORK_PATCH`
- `USER_GATE`
- `COMPLETE`
- `ABORT`

`USER_GATE` means missing operator intent, approval, evidence, or claim
boundary prevents responsible progress.

## Failure Routing

Every finding must name:

- `finding_id`
- `severity`
- `location`
- `root_cause`
- `owning_phase`
- `required_artifact`
- `fix_action`
- `downstream_risk`

Route back to the owning phase. Do not repair the final `.tex` directly when
the underlying artifact is absent or stale.

## No Direct Final Patch

LaTeX patching is allowed only in `patch`, and only from
`latex_patch_plan.md` plus `writing_rationale_matrix.md`. If those artifacts
are shallow, missing, or stale, re-run layout first.
