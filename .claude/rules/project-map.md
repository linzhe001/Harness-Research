---
description: project_map.json 维护规则 — 文件新增或删除时必须同步更新
globs:
  - "src/**/*.py"
  - "baselines/**/*"
  - "configs/**/*.yaml"
  - "configs/**/*.yml"
  - "configs/**/*.json"
  - "scripts/**/*.py"
  - "scripts/**/*.sh"
  - "tests/**/*.py"
---

# project_map.json 维护规则

## Stable vs Volatile 分层

project_map.json 只追踪 **stable 架构文件**（长期存在、定义模块接口的文件）。
**Volatile 实验资产**（per-iteration configs, ablation scripts, one-off utilities）不需要在 project_map.json 中维护。

### Stable（必须追踪）
- `src/**/*.py` — 主研究代码（模型、数据、loss、utils）
- `baselines/` — 每个 baseline 子目录（brief 级别）
- CLAUDE.md `## Entry Scripts` 中列出的核心入口脚本
- CLAUDE.md 中引用的核心配置文件

### Volatile（不需追踪）
- `scripts/run_*.sh` — per-iteration 训练脚本
- `scripts/run_ablation_*.py` — 消融实验脚本
- `configs/` 下的临时实验配置
- `experiments/` 下所有内容

判断标准：如果文件只在 1-2 次迭代中使用，它是 volatile 的。

## 修改代码的正确方式
- **非 trivial 的代码修改**（改逻辑、改接口、改 loss、加模块等）→ 必须调用 `/code-debug`
- **trivial 修改**（typo、注释、import 顺序）→ 可以直接改，但仍须执行以下验证：
  1. `python -m py_compile <file>`
  2. `ruff check --select=E,F,I <file>`
  3. 如涉及接口变更 → 更新 project_map.json（见下方规则）

## project_map.json 何时更新
- **新增 stable 文件** → 在 project_map.json 对应目录下添加节点
- **删除 stable 文件** → 移除对应节点
- **修改接口**（函数签名、tensor shape 变化）→ 更新对应字段
- 仅修改内部实现、不改变接口时，不需要更新
- **新增/删除 volatile 文件** → 不需要更新 project_map.json

## 按目录的描述详细度

### src/ — detailed（主研究代码）
每个文件必须包含：
- `exports`: 导出的类/函数名列表
- `io`: 输入输出 tensor shape（模型相关文件）
- `dependencies`: 依赖的项目内其他模块路径

### baselines/ — brief（复现对比方法）
每个 baseline 子目录只需：
- `description`: 一句话说明
- `source`: 代码来源 URL
- `paper`: 论文引用（作者+会议+年份）
- `status`: verified / untested / modified / broken / partial
- `entry_point`: 训练入口文件
不列出 baseline 内部每个文件的 exports 或 tensor shape。

### configs/, scripts/, docs/ — medium（仅 stable 文件）
每个 stable 文件只需 `description`（用途，1-2句话）。

### experiments/ — minimal
只记录子目录用途和存放规则，不列出具体的日志/checkpoint/结果文件。
