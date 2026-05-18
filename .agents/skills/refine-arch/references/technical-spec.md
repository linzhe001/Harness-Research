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

### 2. first_vertical_slice

Define the first end-to-end path that proves the architecture can work without
spreading implementation across unrelated features.

| Field | Definition |
|-------|------------|
| User / research outcome | |
| Source Artifact | |
| Conclusion Evidence | |
| Entry point | |
| Application service / module | |
| Domain behavior | |
| Persistence / artifact | |
| Output / metric | |
| Acceptance check | |
| Out of scope | |

### 3. module_boundaries

| Module | Owns | Does Not Own | Public API | Depends On | Must Not Depend On | Tests |
|--------|------|--------------|------------|------------|--------------------|-------|
| | | | | | | |

### 4. application_codebase_language_seed

WF6 owns the initial project glossary seed. Write or refresh
`docs/20_facts/Project_Glossary.md` when stable architecture vocabulary is
needed, using only terms grounded in Source Artifacts or architecture decisions.

| Domain Term | Code Term | Definition | Source Artifact | Status |
|-------------|-----------|------------|-----------------|--------|
| | | | | canonical / proposed |

### 5. module_modification_plan

| File | Operation | Description |
|------|-----------|-------------|
| src/models/new_module.py | Add | Core innovation module |
| configs/experiment.yaml | Add | Experiment configuration |

### 6. mvp_definition
- Scope definition (10% data, minimal implementation)
- Validation metrics
- Estimated effort

### 7. alternative_plans

| Decision Point | Plan A | Plan B | Plan C |
|----------------|--------|--------|--------|
| {decision} | Simple/Conservative | Recommended/Balanced | Aggressive/Optimal |

Each plan includes:
- Pros
- Cons
- Applicable scenarios
- Rollback strategy

### 8. integration_points
- Integration points with existing code
- Interfaces that need modification

### 9. resource_estimation

| Stage | GPU Type | VRAM Required | Estimated Duration | Notes |
|-------|----------|---------------|-------------------|-------|
| MVP (10% data) | | | | |
| Full training | | | | |
| Ablation study | | | | |

### 10. risk_mitigation
- Rollback plan for each major change
- Fallback options upon failure
