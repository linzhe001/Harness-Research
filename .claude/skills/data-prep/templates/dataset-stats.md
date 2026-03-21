# Dataset Stats Template

## context_summary Standard Format

```markdown
<context_summary>
- **Project:** {project_name}
- **Current Stage:** WF4 - Data Engineering
- **Prior Inputs:** Sanity_Check_Log.md (GO)
- **Deliverables:** Dataset_Stats.md, Data_Pipeline_Script.py, subset_indices.json
- **Key Conclusions:**
  1. {conclusion_1}
  2. {conclusion_2}
- **Open Issues:** {open_issues}
- **Next Step:** WF5 baseline-repro
</context_summary>
```

## Required Sections

### 1. Full Dataset Statistics

```markdown
## Original Dataset: {dataset_name}

- Total images: {total_images}
- Number of classes: {num_classes}
- Total annotations: {total_annotations}

### Class Distribution
| Class | Sample Count | Proportion |
|------|--------|------|

### BBox Size Distribution
| Size | Count | Proportion |
|------|------|------|
| Small (<32²) | | |
| Medium (32²-96²) | | |
| Large (>96²) | | |
```

### 2. Subset Statistics

```markdown
## Subset (ratio={subset_ratio})

- Number of images: {subset_images}
- Number of annotations: {subset_annotations}
```

### 3. Distribution Comparison

| Metric | Full Dataset | Subset | Deviation |
|------|------|------|------|
| Class distribution | | | <5% |
| Size distribution | | | <5% |

### 4. Validation Results

- [ ] Subset distribution deviation < 5%
- [ ] Random seed fixed
- [ ] subset_indices.json saved
