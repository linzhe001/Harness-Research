# Stage Report Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF7 - Results Analysis
- **Prior Inputs:** Training logs, metrics.json
- **Deliverables:** Stage_Report.md
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** /iterate plan (NEXT_ROUND) / /iterate plan [debug] (DEBUG) / WF9 final-exp (CONTINUE) / WF2 (PIVOT)
</context_summary>
```

## Required Sections

### 1. training_analysis

```markdown
## Training Analysis

### Loss Curves
| Epoch | Train Loss | Val Loss | mAP |
|-------|------------|----------|-----|
| 1 | | | |
| ... | | | |

### Learning Rate
- Initial LR:
- Final LR:
- Warmup epochs:

### Gradient Norm
- Mean:
- Max:
- Stable:
```

### 2. performance_comparison

```markdown
## Performance Comparison

| Metric | Baseline | Ours | Difference | Significance |
|------|----------|--------|------|--------|
| mAP | | | | |
| mAP50 | | | | |
| FPS | | | | |
| Parameters | | | | |
```

### 3. issue_diagnosis

```markdown
## Issue Diagnosis

### Identified Issues
1. [Issue description] → [Severity] → [Recommended action]

### Checklist
- [ ] Loss converged?
- [ ] No overfitting?
- [ ] Gradient norm stable?
- [ ] No NaN/Inf?
```

### 4. scaling_prediction

```markdown
## Full-Scale Training Prediction

Based on scaling law:
- Current (10% data): {current_metric}
- Predicted (100% data): {predicted_metric}
- Confidence interval: [{lower}, {upper}]
- Reference: [10%→100% improvement ratio from similar work]
```

### 5. recommendation

```markdown
## Recommendation

**Decision: NEXT_ROUND / DEBUG / CONTINUE / PIVOT / ABORT**

**Rationale:**
1. ...
2. ...

**Next steps:**
- ...
```

## Decision Matrix

| Scenario | Decision | Next Step |
|------|------|--------|
| Ordinary improvement round, not yet ready for WF9 | NEXT_ROUND | /iterate plan (next round) |
| Bug, stability issue, or pipeline failure | DEBUG | /iterate plan (debug-oriented round) |
| Target met or ready for final experiments | CONTINUE | WF9 (handoff to orchestrator) |
| Fundamental approach change needed | PIVOT | WF2 (alternative approach) |
| Theoretical failure / insufficient resources | ABORT | Record lessons learned and terminate |
