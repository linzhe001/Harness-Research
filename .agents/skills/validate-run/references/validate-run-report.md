# Validate Run Report Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF9 - Validate Run
- **Prior Inputs:** project_map.json, Technical_Spec.md, baseline code, entry scripts
- **Deliverables:** Validate_Run_Report.md
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** WF10 iterate if PASS / $code-debug if FAIL
</context_summary>
```

## Required Sections

### Evidence Sources

| Source | Why It Was Read | Key Facts Used |
|--------|-----------------|----------------|
| `{path_or_command}` | | |

### Semantic Review

| Area | New Code Source | Baseline Source | Result | Findings |
|------|-----------------|-----------------|--------|----------|
| Data pipeline | | | PASS/WARNING/CRITICAL | |
| Model/rendering | | | PASS/WARNING/CRITICAL | |
| Loss | | | PASS/WARNING/CRITICAL | |
| Metrics | | | PASS/WARNING/CRITICAL | |
| Common ML bugs | | | PASS/WARNING/CRITICAL | |

### Review Trace

- **Reviewer status:** used / unavailable / skipped_low_value
- **Trace path:** `{.agents/state/review_traces/...}` or N/A
- **Unresolved critical findings:** ...

### Slice Completion Review

| slice_id | Planned Trace | Implemented Path | Acceptance Result | Feedback Evidence | Status |
|----------|---------------|------------------|-------------------|-------------------|--------|
| | `docs/Implementation_Roadmap.md#...` | | | | PASS/REVIEW/FAIL |

### Language / Boundary / Complexity Review

| Area | Source | Result | Notes |
|------|--------|--------|-------|
| Project glossary usage | `docs/20_facts/Project_Glossary.md` or N/A | PASS/WARNING/CRITICAL/NOT_RUN | |
| Module boundary adherence | `docs/Technical_Spec.md`, `project_map.json` | PASS/WARNING/CRITICAL/NOT_RUN | |
| Public API changes | `project_map.json`, diff | PASS/WARNING/CRITICAL/NOT_RUN | |
| Complexity budget | `docs/Implementation_Roadmap.md#complexity_budget` | PASS/WARNING/CRITICAL/NOT_RUN | |

### Smoke Test Commands

```bash
{command_1}
{command_2}
```

### Smoke Test Results

| Check | Evidence | Status | Notes |
|-------|----------|--------|-------|
| 100-step training | `{log_path}` | PASS/FAIL | |
| checkpoint save/load | `{path_or_command}` | PASS/FAIL | |
| evaluation run | `{log_path}` | PASS/FAIL | |
| wandb | `{log_path_or_url}` | PASS/FAIL/SKIPPED | |
| git_snapshot | `{log_path}` | PASS/FAIL/SKIPPED | |

### Run Artifact Bundle

| Artifact | Path | Status | Notes |
|----------|------|--------|-------|
| resolved config snapshot | `{path}` | PASS/FAIL/NOT_RUN | |
| console log | `{path}` | PASS/FAIL/NOT_RUN | |
| git snapshot | `{path}` | PASS/FAIL/NOT_RUN | |
| eval metrics artifact | `{path}` | PASS/FAIL/NOT_RUN | |
| checkpoint | `{path}` | PASS/FAIL/SKIPPED | |
| commit identity match | `{git_commit}` | PASS/FAIL/NOT_RUN | |

### Verdict

**Decision: PASS / REVIEW / FAIL**

**Rationale:** ...

**Required Fixes:** ...
