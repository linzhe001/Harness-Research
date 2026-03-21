# Environment Refresh Rules

Refresh mode should detect and document:

- Python version
- PyTorch version and CUDA version
- GPU model and VRAM
- dependency file sources such as `requirements*.txt`, `environment*.yml`, `pyproject.toml`
- key ML dependencies only
- conda environment name
- wandb login status when available

Recommended command pattern:

```bash
python --version 2>/dev/null || python3 --version 2>/dev/null
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA {torch.version.cuda}')" 2>/dev/null
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null
pip list 2>/dev/null
echo "$CONDA_DEFAULT_ENV"
python -c "import wandb; api = wandb.Api(); print(api.default_entity)" 2>/dev/null
```

Keep only the relevant summary in `CLAUDE.md`; do not dump raw command output.
When `CLAUDE.md` uses `### Dataset Paths` inside `## Environment`, preserve that subsection unless dataset addresses are explicitly being refreshed.

Update only the `## Environment` section in `CLAUDE.md`.

Never rewrite other sections during refresh mode.
