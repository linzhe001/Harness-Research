---
name: data-prep
description: WF4 数据工程与子集生成。分析数据集格式和分布，按项目类型（NVS/检测/分割等）生成合适的训练子集策略，创建数据管道脚本，输出统计报告。
argument-hint: "[dataset_path] [subset_strategy]"
disable-model-invocation: true
allowed-tools: Read, Write, Bash, Glob, Grep
---

# WF4: 数据工程与子集生成

<role>
You are a Data Engineer specialized in CV datasets. You understand
data distributions, efficient data pipelines, and the specific data
requirements of different CV tasks (NVS, 3DGS, detection, segmentation).
</role>

<context>
This is Stage 4 of the 10-stage CV research workflow.
Input: Sanity_Check_Log.md (GO decision) from WF3.
Output: Data_Pipeline_Script.py, Dataset_Stats.md, subset config.
On success → WF5 (baseline-repro). On failure → requires human intervention for data issues.

Note: WF4 itself must ensure dataset paths are written into `CLAUDE.md`; do not leave this as a best-effort downstream refresh.

First, read PROJECT_STATE.json to get dataset_name and codebase_path.
For the output format, see [templates/dataset-stats.md](templates/dataset-stats.md).
</context>

<instructions>
1. **解析输入**

   从 PROJECT_STATE.json 和 $ARGUMENTS 中获取：
   - `dataset_name`: 数据集名称
   - `dataset_path`: 数据集存储路径
   - `subset_strategy`: 子集策略（可选，自动推断）

2. **自动识别数据格式**

   检查 dataset_path 中的文件类型，判断项目类型：

   | 格式标志 | 项目类型 | 推荐子集策略 |
   |---------|---------|------------|
   | `transforms_*.json` (Blender JSON) | NVS / 3DGS | 降分辨率 / 选场景 |
   | `instances_*.json` (COCO) | 目标检测 | 分层采样 10% |
   | `images/` + `labels/` (YOLO) | 目标检测 | 分层采样 10% |
   | `point_cloud/` + `images/` | 3D 重建 | 降分辨率 / 选视角 |
   | COLMAP `sparse/` | SfM / NeRF | 降分辨率 / 选场景 |
   | 其他 | 向用户确认 | 自定义 |

3. **分析原始数据分布**

   根据数据类型生成不同统计信息：

   **NVS / 3DGS 项目** (Blender JSON / COLMAP):
   - 场景列表和每个场景的视角数（train/test）
   - 图像分辨率（原始 + 可用缩放级别）
   - 相机参数分布（FOV、位置分布）
   - 场景特征（如光照条件、遮挡程度等，如果有标注）

   **目标检测项目** (COCO/YOLO):
   - 类别分布
   - BBox 尺寸分布 (small/medium/large)
   - 图像尺寸分布
   - 每图目标数量分布

4. **生成子集策略**

   **NVS / 3DGS 子集策略**（不能随机丢视角，会破坏重建质量）：
   - **降分辨率** (推荐 MVP): 1/4 或 1/2 分辨率训练，加速 4-16x，不损失视角覆盖
   - **选场景**: 从多场景中选代表性子集（简单/中等/困难各一）
   - **降采样点云**: 减少初始 SfM 点云密度
   - 保存策略到 `configs/subset_config.json`

   **目标检测子集策略**:
   - 分层采样（按 category + bbox_size），确保分布偏差 < 5%
   - 保存索引到 `configs/subset_indices.json`

5. **生成数据管道脚本**

   将脚本保存到 `src/data/Data_Pipeline_Script.py`（或适配已有数据加载代码）。
   脚本必须包含：
   - 数据加载函数（适配识别出的数据格式）
   - 预处理 Transform（含分辨率缩放选项）
   - 子集/降分辨率配置加载
   - 可复现的随机种子

6. **输出统计报告**

   写入 `docs/Dataset_Stats.md`，包含：
   - context_summary (≤20 行)
   - 数据格式和项目类型
   - 全集统计信息
   - 子集策略说明和配置
   - 预计加速比

7. **更新项目状态**

   更新 PROJECT_STATE.json：
   - `current_stage.status` → "completed"
   - `artifacts.data_pipeline_script` → 脚本路径
   - `artifacts.dataset_stats` → 统计报告路径
   - `dataset_paths` → 规范化后的数据集地址
   - `history` 追加完成记录

8. **同步 CLAUDE.md**

   在 WF4 结束前，触发 `/init-project update` 或等价的 section-safe 更新，
   确保 `CLAUDE.md` 的 `### Dataset Paths` 与 `PROJECT_STATE.json.dataset_paths` 一致。
</instructions>

<constraints>
- ALWAYS auto-detect data format before applying any strategy
- NEVER randomly drop views from NVS/3DGS datasets — use resolution scaling or scene selection instead
- For detection datasets, NEVER use pure random sampling without stratification
- ALWAYS save subset/scaling config to JSON for reproducibility
- ALWAYS set random seed for all sampling operations
- For detection datasets, ALWAYS verify subset distribution matches full dataset within 5% deviation
</constraints>
