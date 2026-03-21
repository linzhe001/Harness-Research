---
name: init-project
description: 项目 CLAUDE.md 分阶段生成器。init 模式生成最小版本（Environment + Workflow），update 模式在关键阶段后增量填充（Idea、Structure 等）。
argument-hint: "[init|update]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion
---

# 项目 CLAUDE.md 分阶段生成器

<role>
You are a project documentation specialist. You generate a concise CLAUDE.md
that gives Claude Code all the context it needs. CLAUDE.md is loaded every session,
so every line must earn its place. Keep it under 80 lines.
</role>

<context>
CLAUDE.md 内容在不同工作流阶段才确定：

| 内容 | 确定时机 | 模式 |
|------|---------|------|
| Environment 占位 | init 时 | init |
| Workflow 概览 | init 时 | init |
| Idea 描述 | WF1 survey-idea 之后 | update |
| Tech Stack 细节 | WF2 refine-arch 之后 | update |
| Dataset 路径和统计 | WF4 data-prep 之后 | update |
| Environment 真值 + Baseline 指标参考 | WF5 baseline-repro 之后 | update |
| Project Structure + Core Artifacts | WF6 build-plan 之后 | update |
| Entry Scripts（锁定入口脚本） | WF7 首次实验后 | update |

If PROJECT_STATE.json exists, read it to determine current stage.
If CLAUDE.md already exists, read it first.
For the template format, see [templates/claude-md-template.md](templates/claude-md-template.md).
</context>

<instructions>
## init 模式（$ARGUMENTS 为 "init" 或无参数）

首次生成最小版 CLAUDE.md，只包含**此刻就能确定的信息**。

### 1. 收集信息

通过 AskUserQuestion 向用户收集：
- **项目名** (英文)
- **虚拟环境名**: conda/venv 环境名称（如果已存在；否则允许先留空，WF5 再填）

### 2. 自动检测环境（若当前还没有可运行环境，可跳过并保留占位）

依次运行以下命令（忽略失败的命令）：
```bash
python --version 2>/dev/null || python3 --version 2>/dev/null
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA {torch.version.cuda}')" 2>/dev/null
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null
ls pyproject.toml requirements*.txt setup.py environment.yml 2>/dev/null
pip list 2>/dev/null | grep -iE "torch|torchvision|numpy|opencv|pillow|scipy|timm|mmcv|open3d|plyfile|wandb|tensorboard" 2>/dev/null
```

### 3. 生成最小版 CLAUDE.md

写入以下内容：

```markdown
# {project_name}

<!-- Idea 描述将在 WF1 完成后填入 -->

## Environment
conda activate {env_name}
Python, PyTorch, CUDA, GPU, 依赖版本...

## Tech Stack
<!-- 将在 WF2 完成后填入详细技术栈 -->

## Workflow
WF1(survey) → WF2(arch) → WF3(check) → WF4(data) → WF5(baseline) → WF6(plan) → WF7(code) → WF7.5(validate) → WF8(iterate) → WF9(final-exp) → WF10(release)
WF8 迭代循环: /iterate plan → /iterate code → /iterate run → /iterate eval → (CONTINUE→WF9 | DEBUG→repeat | PIVOT→WF2)
Current stage: WF1 not_started
```

不写 Project Structure、Core Artifacts（WF5 之前不存在）。
不写 Idea 描述（WF1 之前未确认）。

---

## update 模式（$ARGUMENTS 为 "update"）

读取现有 CLAUDE.md 和 PROJECT_STATE.json，根据当前阶段**增量填充**：

### WF1 完成后 → 填入 Idea

读取 `docs/Feasibility_Report.md` 的 context_summary，提取确认后的 Idea 描述。
替换 CLAUDE.md 中的 `<!-- Idea 描述将在 WF1 完成后填入 -->` 为一句话 Idea。

### WF2 完成后 → 填入 Tech Stack

读取 `docs/Technical_Spec.md`，提取：
- 配置管理方式（dataclass / Hydra / argparse）
- Linting 工具
- 实验追踪工具（wandb / tensorboard）
- 基础代码库（如果有）

替换 CLAUDE.md 中 `## Tech Stack` 的占位内容。

### WF4 完成后 → 填入 Dataset

读取 `docs/Dataset_Stats.md`，提取数据集路径、split 信息、关键统计。
替换 CLAUDE.md 中 `### Dataset Paths` 的占位内容。

### WF5 完成后 → 填入 Environment + Baseline 参考

读取 `docs/Baseline_Report.md`，提取主要 baseline 指标。
读取 WF5 已创建的真实环境信息，替换 `## Environment` 中的占位内容。
在数据集路径 section 之后添加 baseline 参考与 evaluation protocol 摘要。

### WF6 完成后 → 填入 Structure + Artifacts

读取 `project_map.json`，提取顶层目录结构。
填入：
- `## Project Structure` — 顶层目录一览 + 描述详细度标注
- `## Core Artifacts` — project_map.json 和 PROJECT_STATE.json
- `## Global Rule` — project_map.json 维护规则引用

### WF7 首次实验后 → 锁定 Entry Scripts

当 WF7 (code-expert) 完成且首次训练/评估成功后，**扫描 `scripts/` 目录**，将实际使用的入口脚本路径写入 CLAUDE.md `## Entry Scripts` section。

步骤：
1. 扫描 `scripts/` 目录中的 `.py` 和 `.sh` 文件
2. 按用途分类：train（训练）、eval（评估）、test/submit（测试/提交）、utils（辅助）
3. 写入 CLAUDE.md 格式：
   ```markdown
   ## Entry Scripts
   以下为锁定的核心入口脚本，迭代阶段**优先修改这些文件**：
   - Train: `scripts/train.py`
   - Eval: `scripts/eval.py`
   - Multi-scene: `scripts/train_all.py`
   辅助脚本（如 ablation runner、submission packager）可按需创建于 `scripts/`，
   但核心训练/评估逻辑必须保留在上述入口脚本中。
   ```

此 section 一旦写入，对后续所有 `/iterate code` 和 `/code-debug` 调用生效。

### `deps-changed` 模式

当依赖文件变更时（由 `deps-update` rule 提醒），仅重新检测环境并更新 `## Environment` section。
等价于 `/env-setup refresh` 的效果。

### 通用更新逻辑

每次 update 都：
- 重新检测 Environment（版本可能变化）
- 更新 `Current stage` 行
- 保留 `## Custom` section 的内容（用户手动添加的）
- 不覆盖已填入的有效内容

---

## 写入规则

- 如果 CLAUDE.md 不存在 → 创建
- 如果 CLAUDE.md 存在 → 使用 Edit 工具精确替换对应 section，不重写整个文件
</instructions>

<constraints>
- CLAUDE.md 总行数 NEVER 超过 120 行（初始 init ≤40 行，后续阶段增量填充）
- NEVER 在 init 模式下填入 Idea、Project Structure、Core Artifacts（尚未确认的内容）
- NEVER 在 Idea 描述中使用学术术语堆砌，保持口语化
- NEVER 列出不相关的依赖（如 setuptools、pip 自身）
- ALWAYS 包含虚拟环境激活命令
- ALWAYS 自动检测而非手动填写技术栈版本
- ALWAYS 保留 `## Custom` section 的用户内容
</constraints>
