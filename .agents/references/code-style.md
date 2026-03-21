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

## Enforcement Guidance

- Treat this file as a style reference, not as an automatic hook.
- Enforce it through the active skill, linting commands, and review discipline.
