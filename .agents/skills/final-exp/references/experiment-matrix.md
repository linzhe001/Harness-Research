# Final Experiment Matrix Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF8 - Ablation Experiment Plan
- **Prior Inputs:** Stage_Report.md (CONTINUE)
- **Deliverables:** Final_Experiment_Matrix.md
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** Execute experiments → Paper writing
</context_summary>
```

## Required Sections

### 1. ablation_table

```markdown
## Ablation Experiments

| Experiment ID | Component A | Component B | Component C | Expected Result |
|---------|-------------|-------------|-------------|----------|
| Baseline | OFF | OFF | OFF | Baseline performance |
| Exp-1 | ON | OFF | OFF | Validate A's contribution |
| Exp-2 | OFF | ON | OFF | Validate B's contribution |
| Exp-3 | OFF | OFF | ON | Validate C's contribution |
| Exp-AB | ON | ON | OFF | Validate A+B synergy |
| Full | ON | ON | ON | Complete method |

Principle: Each experiment changes only one variable
```

### 2. hyperparameter_search

```yaml
search_space:
  learning_rate: [1e-4, 5e-4, 1e-3]
  weight_decay: [0, 1e-4, 1e-3]
  batch_size: [8, 16, 32]
  # Other key hyperparameters

search_strategy: grid  # or random
total_trials: N
```

### 3. robustness_tests

```markdown
## Robustness Tests

| Test Scenario | Description | Expected Behavior |
|---------|------|---------|
| Resolution variation | Input [640, 800, 1024] | Graceful performance degradation |
| Extreme lighting | Overexposed/underexposed images | Detection still effective |
| Heavy occlusion | >50% occlusion | Partial detection |
| OOD data | Classes outside training set | Reasonable rejection |
```

### 4. cross_dataset_evaluation

```markdown
## Cross-Dataset Evaluation

| Dataset | Purpose | Expected Metric |
|--------|------|---------|
| COCO | Primary dataset, full evaluation | mAP ≥ X |
| VOC | Transfer validation | mAP ≥ Y |
| Objects365 | Generalization validation | mAP ≥ Z |
```

### 5. computation_budget

```markdown
## Computation Budget

| Experiment Type | Count | Duration per Run | GPU Type | Total |
|----------|------|----------|---------|------|
| Ablation experiments | N | Xh | V100 | NXh |
| Hyperparameter search | M | Yh | V100 | MYh |
| Robustness tests | K | Zh | V100 | KZh |
| Cross-dataset | J | Wh | V100 | JWh |
| **Total** | | | | **XXh** |

Estimated total cost: $YYY (based on cloud GPU pricing)
```

### 6. execution_order

```markdown
## Execution Order

1. **Phase 1 (parallel):** Ablation experiments Exp-1, Exp-2, Exp-3
2. **Phase 2 (sequential):** Select best combination based on Phase 1 results
3. **Phase 3 (parallel):** Hyperparameter search
4. **Phase 4 (sequential):** Final model full-scale training
5. **Phase 5 (parallel):** Robustness tests + cross-dataset evaluation
```
