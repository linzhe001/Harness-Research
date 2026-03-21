# Sanity Check Log Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF3 - Secondary Validation
- **Prior Inputs:** Technical_Spec.md
- **Deliverables:** Sanity_Check_Log.md
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** WF4 data-prep (if GO) / WF2 rollback (if NO-GO)
</context_summary>
```

## Required Sections

### 1. failure_case_search_results
- Negative results found in search
- Failure cases and their causes

### 2. theoretical_analysis
Challenges to each key assumption:
- Assumption 1: [Description] → Counterexample? Failure conditions?
- Assumption 2: [Description] → Mathematical proof? Experimental validation?

### 3. performance_estimation

| Scenario | Estimated Performance | Basis |
|------|---------|------|
| Upper bound (optimistic) | | |
| Expected value (most likely) | | |
| Lower bound (pessimistic) | | |

### 4. risk_matrix

| Risk Item | Probability (1-5) | Impact (1-5) | Risk Score | Mitigation |
|--------|-----------|-----------|--------|----------|
| Training does not converge | | | | |
| Performance below target | | | | |
| Insufficient compute resources | | | | |

### 5. go_nogo_recommendation

**Decision: GO / CONDITIONAL GO / NO-GO**

**Rationale:** ...

**Conditions (if CONDITIONAL GO):**
1. ...
2. ...

**Recommended next step:** ...
