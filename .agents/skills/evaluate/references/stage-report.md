# Iteration / Stage Report Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF8 - Results Analysis
- **Prior Inputs:** Training logs, eval output, baseline protocol
- **Deliverables:** `docs/iterations/iter{N}.md` or `Stage_Report.md`
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** WF9 final-exp (CONTINUE) / $iterate plan (DEBUG) / WF2 (PIVOT)
</context_summary>
```

## Required Sections

### 1. training_analysis

```markdown
## Training Analysis

### Loss Curves
| Step/Epoch | Train Loss | Val Loss | Key Training Trace |
|------------|------------|----------|--------------------|
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
|--------|----------|------|------------|-------------|
| {metric_1} | | | | |
| {metric_2} | | | | |
| {metric_3} | | | | |
```

### 3. issue_diagnosis

```markdown
## Issue Diagnosis

### Identified Issues
1. [Issue description] → [Severity] → [Recommended action]

### Checklist
- [ ] Loss converging?
- [ ] No overfitting?
- [ ] Gradient norm stable?
- [ ] No NaN/Inf?
```

### 4. scaling_prediction

```markdown
## Full-Scale Training Prediction

Based on current protocol and existing experiments:
- Current proxy results: {current_metric_summary}
- Predicted full run: {predicted_metric_summary}
- Confidence interval: [{lower}, {upper}]
- Reference: {reference_or_reasoning}
```

### 5. recommendation

```markdown
## Recommendation

**Decision: CONTINUE / DEBUG / PIVOT / ABORT**

**Rationale:**
1. ...
2. ...

**Next Steps:**
- ...
```

## Decision Matrix

| Situation | Decision | Next Step |
|-----------|----------|-----------|
| Performance on target + stable training | CONTINUE | WF9 |
| Fixable bugs exist | DEBUG | WF8 new iteration |
| Performance gap >5% | PIVOT | WF2 (alternative approach) |
| Theoretical failure / insufficient resources | ABORT | Record lessons and terminate |
