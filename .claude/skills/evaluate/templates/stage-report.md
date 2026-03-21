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
- **Next Step:** WF9 final-exp (CONTINUE) / /iterate plan (DEBUG) / WF2 (PIVOT)
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

**Decision: CONTINUE / DEBUG / PIVOT / ABORT**

**Rationale:**
1. ...
2. ...

**Next steps:**
- ...
```

## Decision Matrix

| Scenario | Decision | Next Step |
|------|------|--------|
| Performance on target + training stable | CONTINUE | WF8 |
| Fixable bug found | DEBUG | WF6 (with error info) |
| Performance gap >5% | PIVOT | WF2 (alternative approach) |
| Theoretical failure / insufficient resources | ABORT | Record lessons learned and terminate |
