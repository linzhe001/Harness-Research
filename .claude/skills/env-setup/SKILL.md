---
name: env-setup
description: 环境创建与刷新工具。create 模式创建新 conda 环境，refresh 模式检测当前环境并同步 CLAUDE.md 的 Environment 部分。当依赖变化或需要初始化环境时使用。
argument-hint: "[create|refresh]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# 环境创建与刷新工具

<role>
You are a DevOps Engineer who manages Python environments for ML research projects.
You ensure environments are reproducible and documentation stays in sync.
</role>

<context>
This is a utility skill (not a numbered workflow stage). It can be called:
- By the user or other skills when dependencies change (refresh mode)
- As a maintenance fallback when the WF5-created environment needs repair
- Automatically suggested by the `deps-update` rule when dependency files are modified

Sub-commands:
- `create` — Create a new conda environment from scratch as a maintenance action
- `refresh` — Detect current environment and update CLAUDE.md `## Environment` section
</context>

<instructions>
## `create` 模式（$ARGUMENTS 包含 "create"）

1. 向用户询问（AskUserQuestion）：
   - conda 环境名称
   - Python 版本（默认 3.12）
   - 是否有 requirements.txt / environment.yml / pyproject.toml

2. 创建 conda 环境：
   ```bash
   conda create -n {env_name} python={python_version} -y
   conda activate {env_name}
   ```

3. 如果有依赖文件：
   ```bash
   pip install -r requirements.txt  # 或 conda env update -f environment.yml
   ```

4. **设置 wandb**：
   ```bash
   # 检查 wandb 是否已安装
   pip show wandb 2>/dev/null
   ```
   - 如果未安装 → `pip install wandb`
   - 检查登录状态：
     ```bash
     python -c "import wandb; wandb.Api()" 2>&1
     ```
   - 如果未登录 → 提示用户运行 `wandb login`，或通过 AskUserQuestion 询问 API key 后执行：
     ```bash
     wandb login {api_key}
     ```
   - 验证登录成功：
     ```bash
     python -c "import wandb; api = wandb.Api(); print(f'wandb logged in as: {api.default_entity}')"
     ```

5. 运行 `refresh` 逻辑（见下方）更新 CLAUDE.md。

## `refresh` 模式（$ARGUMENTS 包含 "refresh" 或无参数）

1. **自动检测环境**（不询问用户）：
   ```bash
   # Python version
   python --version 2>/dev/null || python3 --version 2>/dev/null

   # PyTorch + CUDA
   python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA {torch.version.cuda}')" 2>/dev/null

   # GPU info
   nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null

   # Dependency files
   ls pyproject.toml requirements*.txt setup.py environment.yml 2>/dev/null

   # Key ML dependencies
   pip list 2>/dev/null | grep -iE "torch|torchvision|numpy|opencv|pillow|scipy|timm|mmcv|open3d|plyfile|wandb|tensorboard|gsplat" 2>/dev/null

   # Conda env name
   echo $CONDA_DEFAULT_ENV 2>/dev/null

   # wandb status
   python -c "import wandb; api = wandb.Api(); print(f'wandb: {api.default_entity}')" 2>/dev/null || echo "wandb: not logged in"
   ```

2. **读取现有 CLAUDE.md**

3. **使用 Edit 工具替换 `## Environment` section**
   仅替换从 `## Environment` 到下一个 `##` 之间的内容。
   格式：
   ```markdown
   ## Environment
   ```bash
   conda activate {env_name}
   ```
   - Python {version}
   - PyTorch {version} (CUDA {version})
   - Key deps: {dep1} {ver1}, {dep2} {ver2}, ...
   - Tracking: wandb ({entity}) / tensorboard
   - GPU: {gpu_name} ({vram})
   ```

4. 不触碰 CLAUDE.md 的其他 section。
</instructions>

<constraints>
- ONLY touch the `## Environment` section of CLAUDE.md — never modify other sections
- ALWAYS auto-detect, never ask the user for version numbers
- ALWAYS preserve the conda activate command
- NEVER list internal/meta packages (pip, setuptools, wheel)
- If CLAUDE.md doesn't exist, inform the user to run `/init-project init` first
</constraints>
