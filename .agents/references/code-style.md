# Code Style Spec

## Type

- `always_on`
- `reference_spec`

## Purpose

Define the baseline coding style for the project so implementation skills follow a consistent standard without pretending this file is an auto-triggered rule.

## Scope

Use this spec when writing or refactoring project code, especially under:

- `src/`
- `scripts/`
- `tests/`
- durable configs and supporting utilities

`Scope` means these file families should follow this style guide. Individual
sections can still narrow their own target. For example, the fail-fast runtime
rules below apply to executable project code, while the test assertion policy
applies to `tests/**`.

## Pre-Edit Checklist

Before editing code:

- Re-read the target files and nearby local patterns in the current turn.
- Prefer the smallest readable change that solves the request.
- Keep functions and classes focused; split code only when it reduces real complexity.
- Use explicit names and straightforward control flow instead of clever one-liners.
- Preserve fail-fast behavior; do not hide invalid state with broad fallbacks.
- Avoid unrelated refactors, formatting churn, and style rewrites outside the touched scope.
- Before changing stable implementation files, read
  `.agents/references/project-map-rule.md`; update `project_map.json` when a
  stable file is added, deleted, renamed, or when stable interfaces,
  responsibilities, exports, config schema, or tensor shapes change.
- Add or update focused tests when behavior changes.
- Run the phase-appropriate validation commands, or state clearly why they could not run.

## Linting Levels

### MVP Phase

```bash
ruff check --select=E,F,I
python -m py_compile *.py
```

### Main Experiment Phase

```bash
ruff check --select=E,W,F,I,N,D,UP --ignore=D100,D104
```

### Release Phase

```bash
ruff check --select=E,W,F,I,N,D,UP,ANN --ignore=ANN101,ANN102,D100,D104
mypy --strict --ignore-missing-imports
```

## Type Hint Guidance

### Lightweight Commented Shapes

Recommended for MVP work:

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

### Structured Tensor Type Aliases

Recommended for more mature code:

```python
from jaxtyping import Float, Int
from torch import Tensor
from typing import TypeAlias

BatchImages: TypeAlias = Float[Tensor, "batch channels height width"]
PointPositions: TypeAlias = Float[Tensor, "num_points 3"]
PointFeatures: TypeAlias = Float[Tensor, "num_points feat_dim 3"]
```

## Docstring Style

Prefer Google-style docstrings for public or non-trivial functions:

```python
def forward_pass(
    images: Tensor,
    features: Tensor,
    targets: Tensor,
    mask: Tensor | None = None,
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

## Config Style

Prefer dataclass-based config structure for durable Python config objects:

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class DataConfig:
    dataset_name: str = "default"
    data_root: Path = Path("/data/scenes")
    resolution_scale: int = 1

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

## File Size Guidance

| File type | Preferred upper bound | Split strategy |
|---|---:|---|
| model definitions | 300 lines | split by rendering, heads, or submodules |
| data handling | 200 lines | split into dataset, transforms, samplers |
| training scripts | 300 lines | split into entrypoint, trainer, callbacks |
| utility modules | 200 lines | split by responsibility under `utils/` |

## Training Script Expectations

Training scripts should generally include:

- deterministic seed setup
- gradient clipping when appropriate
- learning-rate scheduling
- periodic checkpoint saving
- tracking through tensorboard or wandb
- config-driven execution through `--config` or the project standard equivalent

## Fail-Fast Error Policy

- Do not introduce fallback behavior that hides invalid state, missing data, bad configuration, import errors, shape mismatches, or failed optional dependencies.
- Do not add broad `try`/`except` blocks, silent `except` handlers, default substitute values, or best-effort continuation paths unless the user explicitly requests tolerant behavior for a specific boundary.
- Do not silently substitute an empty string for missing semantic data. Required values such as dataset names, metric names, contract statuses, run IDs, evidence references, paths, or claim boundaries must raise an explicit error when absent. Optional values may fall back only with an explicit warning that names the field, source, and fallback behavior.
- Do not add `assert` statements in runtime code. For conditions that must be checked, use explicit validation and raise `ValueError`, `TypeError`, `RuntimeError`, or the narrowest appropriate exception with actionable context.
- Let unexpected errors propagate so the failing command, stack trace, and root cause remain visible during development, training, and evaluation.

## Test Assertion Policy

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

## Enforcement Guidance

- Treat this file as a style reference, not as an automatic hook.
- Enforce it through the active skill, linting commands, and review discipline.
