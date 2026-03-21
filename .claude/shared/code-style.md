# CV 研究代码风格规范

本规范定义所有 CV 研究项目代码必须遵循的风格标准。

## 1. 分阶段 Linting 规则

### MVP 阶段 (快速验证)
```bash
ruff check --select=E,F,I
python -m py_compile *.py
```

### 主实验阶段
```bash
ruff check --select=E,W,F,I,N,D,UP --ignore=D100,D104
```

### 发布阶段
```bash
ruff check --select=E,W,F,I,N,D,UP,ANN --ignore=ANN101,ANN102,D100,D104
mypy --strict --ignore-missing-imports
```

## 2. Type Hints 规范

### 注释说明方案 (推荐 MVP 使用)

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

### jaxtyping 方案 (推荐正式项目使用)

```python
from jaxtyping import Float, Int
from torch import Tensor
from typing import TypeAlias

BatchImages: TypeAlias = Float[Tensor, "batch channels height width"]
PointPositions: TypeAlias = Float[Tensor, "num_points 3"]
PointFeatures: TypeAlias = Float[Tensor, "num_points feat_dim 3"]
```

## 3. Docstring 模板 (Google Style)

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

## 4. Config 管理 (dataclass-based)

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

## 5. 文件长度限制

| 文件类型 | 最大行数 | 超出后拆分方式 |
|---------|---------|-------------|
| 模型定义 | 300 | 按功能拆分 (model.py, rendering.py, etc.) |
| 数据处理 | 200 | dataset.py, transforms.py, samplers.py |
| 训练脚本 | 300 | train.py, trainer.py, callbacks.py |
| 工具函数 | 200 | utils/ 子目录按功能拆分 |

## 6. 训练脚本必备要素

- `set_seed()`: 设置所有随机种子
- Gradient clipping
- Learning rate scheduler
- Checkpoint saving (定期)
- Logging (tensorboard / wandb)
- 支持 `--config` 参数驱动
