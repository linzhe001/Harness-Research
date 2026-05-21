# Auto-Iterate Goal

## Objective

### Primary Metric
- **name**: SSIM
- **direction**: maximize
- **target**: 0.95

### Constraints
- FPS >= 30

## Patience
- **max_no_improve_rounds**: 5
- **min_primary_delta**: 0.01

## Budget
- **max_rounds**: 20
- **max_gpu_hours**: 100.0

## Screening Policy
- **enabled**: true
- **threshold_pct**: 90
- **default_steps**: 5000

## Initial Hypotheses
1. Perceptual loss should directly optimize SSIM.

## Forbidden Directions
- None specified.
