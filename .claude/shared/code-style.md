# CV Research Code Style Guide

This guide defines the style standards that all CV research project code must follow.

## 1. Staged Linting Rules

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

## 2. Type Hints Guidelines

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

## 3. Docstring Template (Google Style)

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

## 4. Config Management (dataclass-based)

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

## 5. File Length Limits

| File Type | Max Lines | Split Strategy When Exceeded |
|-----------|-----------|------------------------------|
| Model definition | 300 | Split by functionality (model.py, rendering.py, etc.) |
| Data processing | 200 | dataset.py, transforms.py, samplers.py |
| Training script | 300 | train.py, trainer.py, callbacks.py |
| Utility functions | 200 | Split into utils/ subdirectories by functionality |

## 6. Required Elements in Training Scripts

- `set_seed()`: Set all random seeds
- Gradient clipping
- Learning rate scheduler
- Checkpoint saving (periodic)
- Logging (tensorboard / wandb)
- Support `--config` parameter-driven execution
