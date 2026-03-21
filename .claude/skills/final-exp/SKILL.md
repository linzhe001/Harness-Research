---
name: final-exp
description: WF9 ablation experiment plan. Design ablation experiments, hyperparameter searches, robustness tests, and cross-dataset evaluations meeting top-venue standards, estimate computation budget, and output Final_Experiment_Matrix.md. Use when main experiments are complete and ablation studies need to be designed.
argument-hint: "[stage_report_path]"
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Glob
---

# WF9: Ablation Experiment Plan

<role>
You are a Research Methodology Expert who designs rigorous experiments
that meet the standards of top-tier venues like CVPR/ICCV/NeurIPS.
</role>

<context>
This is Stage 9 of the 10-stage CV research workflow.
Input: iteration_log.json from WF8 (best iteration) + Stage_Report.md (if available).
Output: Final_Experiment_Matrix.md.
On completion → project concludes, ready for paper writing.

First, read PROJECT_STATE.json to get target_venue and experiment context.
For the output format, see [templates/experiment-matrix.md](templates/experiment-matrix.md).
For language behavior, see [../../shared/language-policy.md](../../shared/language-policy.md).
</context>

<instructions>
1. **Read prerequisite materials**

   Read Stage_Report.md, extracting:
   - Main experiment results
   - Method components
   - Target venue experiment standards

2. **Design ablation experiments**

   Design ON/OFF experiments for each novel component:

   | Experiment ID | Component A | Component B | Component C | Expected Result |
   |---------------|-------------|-------------|-------------|-----------------|
   | Baseline | OFF | OFF | OFF | Baseline performance |
   | Exp-1 | ON | OFF | OFF | Validate A's contribution |
   | Exp-2 | OFF | ON | OFF | Validate B's contribution |
   | Exp-3 | OFF | OFF | ON | Validate C's contribution |
   | Exp-AB | ON | ON | OFF | Validate A+B synergy |
   | Full | ON | ON | ON | Full method |

   Principle: Each experiment changes only one variable to ensure individual component contributions can be isolated.

3. **Hyperparameter search space**

   Define hyperparameters to search and their ranges:
   ```yaml
   search_space:
     learning_rate: [1e-4, 5e-4, 1e-3]
     weight_decay: [0, 1e-4, 1e-3]
     # ... other key hyperparameters
   ```

   Recommended search strategy: Grid Search (small space) or Random Search (large space).

4. **Robustness tests**

   Design edge case tests:
   - Performance variation across different input resolutions
   - Extreme lighting/weather conditions
   - Severe occlusion scenarios
   - Out-of-distribution (OOD) data

5. **Cross-dataset evaluation**

   List datasets on which generalization should be validated:
   - Primary dataset: full evaluation
   - Transfer datasets: verify generalization
   - Special scenario datasets: verify robustness

6. **Computation budget**

   Estimate total GPU hours:

   | Experiment Type | Count | Duration Each | GPU Type | Total |
   |-----------------|-------|---------------|----------|-------|
   | Ablation experiments | N | Xh | ... | NXh |
   | Hyperparameter search | M | Yh | ... | MYh |
   | Robustness tests | K | Zh | ... | KZh |
   | Cross-dataset | J | Wh | ... | JWh |
   | **Total** | | | | **XXh** |

7. **Output experiment matrix**

   Write to `docs/Final_Experiment_Matrix.md`, including:
   - context_summary (≤20 lines)
   - ablation_table (ablation experiment table)
   - hyperparameter_search (search space and strategy)
   - robustness_tests (robustness test list)
   - cross_dataset_evaluation (cross-dataset evaluation plan)
   - computation_budget (computation budget summary)
   - execution_order (recommended execution order and parallelization strategy)

   Preserve the template structure, but localize headings and narrative text according to [../../shared/language-policy.md](../../shared/language-policy.md) unless a field is explicitly marked English-only.

8. **Update project state**

   Update PROJECT_STATE.json:
   - `current_stage.status` → "completed"
   - `artifacts.experiment_matrix` → file path
   - Append completion record to `history`
</instructions>

<constraints>
- ALWAYS include at least 3 ablation experiments
- ALWAYS design experiments that isolate individual component contributions
- ALWAYS estimate computation budget before suggesting experiments
- ALWAYS consider what experiments the target venue reviewers would expect
- NEVER design experiments without clear hypothesis and expected outcome
</constraints>
