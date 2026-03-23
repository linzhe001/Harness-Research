# Auto-Iterate Goal

> This file defines the research objective for the auto-iterate controller.
> The controller's goal parser extracts structured fields from the headings and
> field lines below. Keep the format consistent — do not remove required headings.
>
> After editing, run `tooling/auto_iterate/scripts/auto_iterate_ctl.sh start --goal docs/auto_iterate_goal.md`
> or use the `$auto-iterate-goal check` skill to validate before launching.

## Objective

### Primary Metric
- **name**: {{METRIC_NAME}}
- **direction**: {{maximize|minimize}}
- **target**: {{TARGET_VALUE}}

### Constraints
<!-- List hard constraints that must not be violated. One per line. -->
- {{CONSTRAINT_1}}
- {{CONSTRAINT_2}}

## Patience
- **max_no_improve_rounds**: {{5}}
- **min_primary_delta**: {{0.1}}

## Budget
- **max_rounds**: {{20}}
- **max_gpu_hours**: {{100.0}}

## Screening Policy
- **enabled**: {{true|false}}
- **threshold_pct**: {{90}}
- **default_steps**: {{5000}}

## Initial Hypotheses
<!-- Seed hypotheses for the first few rounds. The controller's plan phase will
     use these as starting points and generate new hypotheses as it learns. -->
1. {{HYPOTHESIS_1}}
2. {{HYPOTHESIS_2}}
3. {{HYPOTHESIS_3}}

## Forbidden Directions
<!-- Hard boundaries the AI must never cross, regardless of potential metric gains. -->
- {{FORBIDDEN_1}}
- {{FORBIDDEN_2}}
