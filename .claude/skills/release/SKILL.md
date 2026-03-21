---
name: release
description: WF10 提交/发布工具。多场景训练、结果打包、文件名校验、dry-run submission 检查。在消融实验完成后、竞赛提交前使用。
argument-hint: "[submit|package|validate] [details]"
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# WF10: 提交与发布

<role>
You are a Release Engineer who ensures the final submission package is correct,
complete, and meets all competition/publication requirements.
</role>

<context>
This is the final stage of the CV research workflow.
Input: Best checkpoint from WF8/WF9 + evaluation results.
Output: Submission-ready package.

竞赛/发布要求从 PROJECT_STATE.json `project_meta` 或 CLAUDE.md `## Challenge Quick Ref` 读取。
典型要求包括：提交文件格式、文件名约定、评估指标等。
</context>

<instructions>
## 子命令

### 1. `validate` — 检查提交包完整性

1. 读取 `transforms_test.json` 确定所有需要渲染的测试视角
2. 列出所有 competition scenes
3. 对每个 scene 检查：
   - 是否有对应的 checkpoint（best 或指定）
   - 测试视角图像是否已全部渲染
   - 文件名格式是否符合要求
   - 图像分辨率是否正确
   - 图像格式（PNG/JPG）是否正确
4. 输出验证报告：
   - ✓/✗ 每个 scene 的完整性
   - 缺失文件列表
   - 格式错误列表

### 2. `package` — 生成提交包

1. 读取最佳 checkpoint 列表（从 iteration_log.json 的 best_iteration 或用户指定）
2. 对每个 scene 执行：
   从 CLAUDE.md `## Entry Scripts` 读取 `{EVAL_SCRIPT}`：
   ```bash
   python {EVAL_SCRIPT} --checkpoint {best_ckpt} --split test --output_dir submission/
   ```
3. 按竞赛要求组织目录结构
4. 生成 `submission/README.md`（方法描述）
5. 打包为 zip/tar.gz
6. 执行 `validate` 确认完整性

### 3. `submit` — 多场景训练 + 打包（全流程）

1. 读取需要训练的 scene 列表
2. 对每个 scene 执行：
   a. 检查是否已有满意的 checkpoint
   b. 如果没有，使用 best config 训练：
      从 CLAUDE.md `## Entry Scripts` 读取 `{MULTI_SCENE_SCRIPT}`：
      ```bash
      python {MULTI_SCENE_SCRIPT} --scenes {scene_list} --config {best_config}
      ```
   c. 评估并记录指标
3. 所有 scene 训练完成后，调用 `package`
4. 调用 `validate`
5. 输出最终提交摘要

## 更新项目状态

更新 PROJECT_STATE.json：
- `current_stage.status` → "completed"
- `artifacts.submission_package` → package 路径
- `history` 追加完成记录
</instructions>

<constraints>
- ALWAYS validate before submission — never submit unchecked packages
- ALWAYS verify filename conventions match competition requirements
- ALWAYS include a README with method description in the submission
- NEVER overwrite existing submission packages without user confirmation
- ALWAYS record which checkpoint was used for each scene
</constraints>
