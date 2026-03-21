# Validate Run Review Checklist

Use this checklist before entering WF8.

## Semantic Review

Check equivalence against the chosen verified baseline for:

- data normalization and channel order
- train/test split logic
- camera parsing and coordinate conventions
- model initialization behavior
- forward-pass equivalence for preserved baseline components
- shared loss computation
- metric computation details:
  - PSNR range, clamp, border handling
  - SSIM window and `data_range`
  - LPIPS backbone choice
  - output post-processing and save format
- common ML bugs:
  - detached gradients
  - in-place autograd corruption
  - CPU/GPU device mismatch
  - scheduler step timing

## Smoke Test

Run the short validation chain:

1. 100-step training
2. checkpoint save
3. checkpoint load
4. evaluation pass
5. wandb initialization
6. `git_snapshot` verification if present

## Result Classes

- `PASS`: smoke test passed and no critical semantic issue
- `REVIEW`: smoke test passed but semantic review found critical concerns
- `FAIL`: smoke test failed
