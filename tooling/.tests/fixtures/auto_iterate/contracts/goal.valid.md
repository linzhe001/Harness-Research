# Auto-Iterate Goal

## Objective

### Primary Metric
- **name**: PSNR
- **direction**: maximize
- **target**: 32.0

### Constraints
- FPS >= 30
- Parameters <= 50M

## Patience
- **max_no_improve_rounds**: 5
- **min_primary_delta**: 0.1

## Budget
- **max_rounds**: 20
- **max_gpu_hours**: 100.0

## Screening Policy
- **enabled**: true
- **threshold_pct**: 90
- **default_steps**: 5000

## Initial Hypotheses
1. Adding channel attention to the decoder skip connections should improve detail reconstruction.
2. Replacing L1 loss with a hybrid SSIM+L1 loss may improve perceptual quality.
3. Increasing the feature dimension from 64 to 128 in the bottleneck could capture more fine-grained information.

## Forbidden Directions
- Do not replace the backbone architecture entirely (keep the current ResNet-based encoder).
- Do not reduce input resolution below 256x256.
