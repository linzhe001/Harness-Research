# Implementation Roadmap Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF7 - Implementation Planning
- **Prior Inputs:** Technical_Spec.md, Dataset_Stats.md
- **Deliverables:** Implementation_Roadmap.md
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** WF8 code-expert
</context_summary>
```

## Required Sections

### 0. evidence_sources

| Source | Why It Was Read | Key Facts Used |
|--------|-----------------|----------------|
| `{path_or_command}` | | |

### 1. file_tree

```
project_root/
├── configs/
│   ├── base.yaml
│   └── experiments/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   ├── backbone.py
│   │   ├── neck.py
│   │   └── head.py
│   ├── data/
│   │   ├── dataset.py
│   │   └── transforms.py
│   ├── losses/
│   └── utils/
│       ├── registry.py
│       └── config.py
├── scripts/
│   ├── train.py
│   └── eval.py
└── tests/
```

### 2. slice_plan

Roadmap tasks must be ordered as vertical slices before any broad layer-by-layer
expansion. Each slice should be small enough to review and must have a feedback
command.

#### Slice Trace: {slice_id}

- User / research outcome:
- Source Artifact:
- Conclusion Evidence:
- Design anchor: `docs/Technical_Spec.md#...`
- Planned files:
- Public interfaces:
- Test / smoke command:
- Gate Evidence target:
- Downstream validation doc:
- Commit boundary:
- Suggested commit message:
- Out of scope:

| slice_id | Outcome | Path | Acceptance | Tests / feedback | Dependencies |
|----------|---------|------|------------|------------------|--------------|
| | | UI/CLI -> service/module -> domain behavior -> artifact -> output | | | |

### 3. module_pseudocode

For each new file, provide:
- Class/function signatures (with Type Hints)
- Core logic pseudocode
- Input/output examples (with tensor shapes)
- Dependency relationships
- Interface contracts: accepted input types, return types, tensor/data shapes,
  required config keys, error conditions, and invariants that downstream code
  may rely on
- Implementation constraints: stable extension points, forbidden shortcuts,
  compatibility requirements with baselines or evaluation scripts, and ownership
  notes for the next code generation step

### 3b. shared_interfaces

List the project-level interfaces that multiple files must agree on:

| Interface | Owner File | Consumers | Signature / Schema | Shape or Type Contract | Failure Behavior |
|---|---|---|---|---|---|
| Dataset item | `src/data/dataset.py` | `scripts/train.py`, model forward | | | |
| Model forward | `src/models/...` | trainer, eval | | | |
| Metric output | `scripts/eval.py` | `$iterate eval`, reports | | | |

### 3c. application_codebase_language_updates

WF7 owns glossary refinement from the approved architecture into executable
implementation language. Update `docs/20_facts/Project_Glossary.md` from stable
files, interfaces, configs, metrics, tests, and error names.

| Proposed Term | Canonical Term | Code Term | Used In | Decision / Reason |
|---------------|----------------|-----------|---------|-------------------|
| | | | | keep / rename / proposed |

### 4. test_plan

Use the smallest feedback loop that can prove each slice.

| slice_id | Red Test / Expected Failure | Green Implementation Scope | Refactor Check | Command | Manual Fallback / NOT_RUN Reason |
|----------|-----------------------------|----------------------------|----------------|---------|----------------------------------|
| | | | | | |

### 4b. commit_plan

Use `.agents/references/sliced-commit-rule.md`. Each completed slice should map
to one commit after its validation or `NOT_RUN` reason is recorded.

| commit_slice | Files / Hunks | Validation Before Commit | Commit Message | Cross-Cutting Reason |
|--------------|---------------|--------------------------|----------------|----------------------|
| `{slice_id}` | | | | |

### 5. config_schema

```yaml
experiment:
  name: str
  seed: int

data:
  dataset_name: str
  batch_size: int

model:
  backbone: dict
  neck: dict
  head: dict

train:
  max_epochs: int
  learning_rate: float
```

### 6. training_pipeline

#### Stage 1: Smoke Test
- Entry conditions: ...
- Execution steps: ...
- Validation checkpoints: ...
- Failure handling: ...

#### Stage 2: Module Integration
- Entry conditions: ...
- Execution steps: ...
- Validation checkpoints: ...
- Failure handling: ...

#### Stage 3: Full Training
- Entry conditions: ...
- Execution steps: ...
- Validation checkpoints: ...
- Failure handling: ...

### 7. validation_checkpoints

| Stage | Check Item | Pass Criteria |
|------|--------|----------|
| Smoke Test | Training can start | No errors |
| Module Integration | Gradient flow is normal | grad_norm > 0 |
| Full Training | Convergence | val_loss decreasing |

### 8. complexity_budget

| Constraint | Budget | Review Notes |
|------------|--------|--------------|
| New public APIs | | |
| New glossary terms | | |
| New dependencies | | |
| Maximum files per slice | | |
| Deletions / simplifications | | |
