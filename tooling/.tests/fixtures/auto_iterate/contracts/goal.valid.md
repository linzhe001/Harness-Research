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

## Automation Policy
- **auto_proceed_flows**: prepare,build,run,analyze,write,change,release_validate
- **manual_approval_flows**: grill_exit,approval_tool,external_submit
- **commit_checkpoint_policy**: pre_train_and_pre_eval_required
- **claim_delta_policy**: record_claim_delta_evidence
- **watchdog_policy**: status_json_only

## Assurance Axes
- metric_quality
- ablation
- claim_support
