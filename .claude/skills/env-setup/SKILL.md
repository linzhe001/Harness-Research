---
name: env-setup
description: Environment creation and refresh tool. Create mode sets up a new conda environment; refresh mode detects the current environment and syncs the Environment section of CLAUDE.md. Use when dependencies change or the environment needs initialization.
argument-hint: "[create|refresh]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Environment Creation and Refresh Tool

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
## `create` Mode ($ARGUMENTS contains "create")

1. Ask the user (AskUserQuestion):
   - conda environment name
   - Python version (default 3.12)
   - Whether there is a requirements.txt / environment.yml / pyproject.toml

2. Create the conda environment:
   ```bash
   conda create -n {env_name} python={python_version} -y
   conda activate {env_name}
   ```

3. If dependency files exist:
   ```bash
   pip install -r requirements.txt  # or conda env update -f environment.yml
   ```

4. **Set up wandb**:
   ```bash
   # Check if wandb is installed
   pip show wandb 2>/dev/null
   ```
   - If not installed → `pip install wandb`
   - Check login status:
     ```bash
     python -c "import wandb; wandb.Api()" 2>&1
     ```
   - If not logged in → prompt the user to run `wandb login`, or use AskUserQuestion to get the API key and then run:
     ```bash
     wandb login {api_key}
     ```
   - Verify login succeeded:
     ```bash
     python -c "import wandb; api = wandb.Api(); print(f'wandb logged in as: {api.default_entity}')"
     ```

5. Run the `refresh` logic (see below) to update CLAUDE.md.

## `refresh` Mode ($ARGUMENTS contains "refresh" or no arguments)

1. **Auto-detect the environment** (do not ask the user):
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

2. **Read the existing CLAUDE.md**

3. **Use the Edit tool to replace the `## Environment` section**
   Only replace the content between `## Environment` and the next `##`.
   Format:
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

4. Do not touch any other sections of CLAUDE.md.
</instructions>

<constraints>
- ONLY touch the `## Environment` section of CLAUDE.md — never modify other sections
- ALWAYS auto-detect, never ask the user for version numbers
- ALWAYS preserve the conda activate command
- NEVER list internal/meta packages (pip, setuptools, wheel)
- If CLAUDE.md doesn't exist, inform the user to run `/init-project init` first
</constraints>
