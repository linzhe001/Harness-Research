# Technical Spec Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF6 - Architecture Design
- **Prior Inputs:** Feasibility_Report.md, Idea_Debate.md, Refined_Idea.md, Dataset_Stats.md, Baseline_Report.md, evaluation contract/protocol
- **Deliverables:** Technical_Spec.md
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** WF7 build-plan or WF6 deep-check design review
</context_summary>
```

## Required Sections

### 0. evidence_sources

| Source | Why It Was Read | Key Facts Used |
|--------|-----------------|----------------|
| `{path_or_command}` | | |

Separate verified facts from inferences. Put unverifiable assumptions under open issues.

### 1. architecture_overview
- Include ASCII architecture diagram
- Data flow description

### 2. module_modification_plan

| File | Operation | Description |
|------|-----------|-------------|
| src/models/new_module.py | Add | Core innovation module |
| configs/experiment.yaml | Add | Experiment configuration |

### 3. mvp_definition
- Scope definition (10% data, minimal implementation)
- Validation metrics
- Estimated effort

### 4. alternative_plans

| Decision Point | Plan A | Plan B | Plan C |
|----------------|--------|--------|--------|
| {decision} | Simple/Conservative | Recommended/Balanced | Aggressive/Optimal |

Each plan includes:
- Pros
- Cons
- Applicable scenarios
- Rollback strategy

### 5. integration_points
- Integration points with existing code
- Interfaces that need modification

### 6. resource_estimation

| Stage | GPU Type | VRAM Required | Estimated Duration | Notes |
|-------|----------|---------------|-------------------|-------|
| MVP (10% data) | | | | |
| Full training | | | | |
| Ablation study | | | | |

### 7. risk_mitigation
- Rollback plan for each major change
- Fallback options upon failure
