# CV Research Code Style Guide

This guide defines the style standards that all Harness research project code must follow.

## 1. Pre-Edit Checklist

Before editing code:

- Re-read the target files and nearby local patterns in the current turn.
- Prefer the smallest readable change that solves the request.
- Keep functions and classes focused; split code only when it reduces real complexity.
- Use explicit names and straightforward control flow instead of clever one-liners.
- Preserve fail-fast behavior; do not hide invalid state with broad fallbacks.
- Avoid unrelated refactors, formatting churn, and style rewrites outside the touched scope.
- Before changing stable implementation files, read `.claude/rules/project-map.md`;
  update `project_map.json` when a stable file is added, deleted, renamed, or
  when stable interfaces, responsibilities, exports, config schema, or tensor
  shapes change. If `docs/20_facts/Codebase_Map.md` exists, update it in the
  same change when stable codebase structure, responsibilities, public
  interfaces, entry points, or dependencies changed.
- Add or update focused tests when behavior changes.
- Run the phase-appropriate validation commands, or state clearly why they could not run.

## 2. Staged Linting Rules

### MVP Stage (Quick Validation)
```bash
ruff check --select=E,F,I
python -m py_compile *.py
```

### Main Experiment Stage
```bash
ruff check --select=E,W,F,I,N,D,UP --ignore=D100,D104
```

### Release Stage
```bash
ruff check --select=E,W,F,I,N,D,UP,ANN --ignore=ANN101,ANN102,D100,D104
mypy --strict --ignore-missing-imports
```

## 3. Type Hints Guidelines

### Comment Annotation Approach (Recommended for MVP)

```python
def forward(
    self,
    images: Tensor,  # shape: (B, C, H, W), normalized to [0, 1]
    targets: list[dict[str, Tensor]] | None = None,
) -> dict[str, Tensor]:
    """Forward pass.

    Args:
        images: Input tensor of shape (B, 3, H, W).
        targets: Optional supervision targets.
    """
```

### jaxtyping Approach (Recommended for Production Projects)

```python
from jaxtyping import Float, Int
from torch import Tensor
from typing import TypeAlias

BatchImages: TypeAlias = Float[Tensor, "batch channels height width"]
PointPositions: TypeAlias = Float[Tensor, "num_points 3"]
PointFeatures: TypeAlias = Float[Tensor, "num_points feat_dim 3"]
```

## 4. Docstring Template (Google Style)

```python
def forward_pass(
    images: Tensor,      # (B, C, H, W)
    features: Tensor,    # (B, D, H, W)
    targets: Tensor,     # (B, num_classes)
    mask: Tensor | None = None,  # (B, 1, H, W)
    temperature: float = 1.0,
) -> tuple[Tensor, Tensor, dict]:
    """Run forward pass through the model.

    Args:
        images: Input images normalized to [0, 1].
        features: Extracted feature maps.
        targets: Ground truth labels or regression targets.
        mask: Optional binary mask for valid regions.
        temperature: Softmax temperature scaling.

    Returns:
        Tuple of (predictions, loss, metrics_dict).
    """
```

## 5. Config Management (dataclass-based)

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class DataConfig:
    dataset_name: str = "default"
    data_root: Path = Path("/data/scenes")
    resolution_scale: int = 1  # downscale factor for MVP

@dataclass
class ModelConfig:
    backbone: str = "resnet50"
    hidden_dim: int = 256

@dataclass
class TrainConfig:
    max_steps: int = 30_000
    learning_rate: float = 1.6e-4
    seed: int = 42

@dataclass
class ExperimentConfig:
    data: DataConfig = field(default_factory=DataConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)
```

## 6. File Length Limits

| File Type | Max Lines | Split Strategy When Exceeded |
|-----------|-----------|------------------------------|
| Model definition | 300 | Split by functionality (model.py, rendering.py, etc.) |
| Data processing | 200 | dataset.py, transforms.py, samplers.py |
| Training script | 300 | train.py, trainer.py, callbacks.py |
| Utility functions | 200 | Split into utils/ subdirectories by functionality |

## 7. Required Elements in Training Scripts

- `set_seed()`: Set all random seeds
- Gradient clipping
- Learning rate scheduler
- Checkpoint saving (periodic)
- Logging (tensorboard / wandb)
- Support `--config` parameter-driven execution

## 8. Fail-Fast Error Policy

- Do not introduce fallback behavior that hides invalid state, missing data, bad configuration, import errors, shape mismatches, or failed optional dependencies.
- Do not add broad `try`/`except` blocks, silent `except` handlers, default substitute values, or best-effort continuation paths unless the user explicitly requests tolerant behavior for a specific boundary.
- Do not silently substitute an empty string for missing semantic data. Required values such as dataset names, metric names, contract statuses, run IDs, evidence references, paths, or claim boundaries must raise an explicit error when absent. Optional values may fall back only with an explicit warning that names the field, source, and fallback behavior.
- Do not add `assert` statements in runtime code. For conditions that must be checked, use explicit validation and raise `ValueError`, `TypeError`, `RuntimeError`, or the narrowest appropriate exception with actionable context.
- Let unexpected errors propagate so the failing command, stack trace, and root cause remain visible during development, training, and evaluation.

## 9. Test Assertion Policy

The style guide applies to `tests/**`, but test code has a narrower assertion
rule than runtime code:

- `tests/**` may and should use pytest `assert` statements for expected values,
  shapes, paths, status flags, and structured output comparisons.
- Test assertions should be specific enough to explain the expected behavior.
  Prefer checking exact values, keys, exceptions, and state transitions over
  broad truthiness checks.
- For expected error paths, use `pytest.raises(...)` and assert on the exception
  message when the message is part of the contract.
- Do not use pytest `assert` as a shortcut inside runtime helpers, fixtures that
  are imported by production code, or scripts outside `tests/**`. Runtime
  validation still needs explicit exceptions.
- Do not make tests tolerant with broad `try`/`except`, swallowed failures, or
  fallback defaults. Tests should fail loudly when the contract is broken.
