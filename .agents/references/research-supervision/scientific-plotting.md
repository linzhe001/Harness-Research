# Scientific Plotting Asset

## Purpose

Use this asset for figure planning, figure contracts, caption audits, and
paper-facing plots. Figures are claim carriers, not decoration.

## Figure Roles

| Role | Purpose | Typical form |
|---|---|---|
| Motivated example | show the real failure, gap, or need | running example, failure case, existing-vs-ours, teaser |
| Solution overview | explain workflow, architecture, or modules | pipeline, system architecture, multi-layer diagram |
| Experimental result | support a result claim or expose a boundary | table, bar, line, heatmap, scatter, box plot, radar, error breakdown |
| Supporting figure | clarify detail or appendix evidence | qualitative case, taxonomy, extra analysis |

The first sentence of a caption should state the visual thesis or finding. The
rest of the caption gives setup, panels, axes, and interpretation boundary.

## Figure Contract

Before drawing, record:

| Field | Question |
|---|---|
| claim_id | Which claim or reader question does this figure support? |
| role | motivated example, solution overview, experimental result, or supporting |
| evidence_source | Which artifact, metric, table, case, or citation supports it? |
| required_data | What exact data or artifact must exist? |
| panel_plan | What each panel shows and why |
| caption_boundary | What the caption may and may not claim |
| generation_owner | plot script, diagram editor, AI sketch, manual vectorization, or USER_GATE |

If a quantitative panel has no data source, write `RUN_REQUEST` or mark the
panel `USER_GATE`. Do not infer numbers from prose.

## Motivated Example

Preferred patterns:

```text
real input
  -> current method failure
  -> corrected behavior or paper insight
```

or:

```text
existing approach
  vs
proposed approach
```

Use a real case or a documented synthetic case. Avoid toy placeholders that do
not reveal the actual failure.

## Solution Overview

Choose the layout by method shape:

| Shape | Use when | Layout |
|---|---|---|
| Pipeline | staged transformation | left-to-right stages with inputs and outputs |
| System architecture | interacting components or agents | system boundary with modules and message/data flow |
| Multi-layer | train/infer, offline/online, or abstraction levels | stacked layers with cross-layer arrows |

Module names must match section headings and implementation names where
possible.

## Experimental Result Charts

| Chart | Best for | Checks |
|---|---|---|
| grouped bar | method x dataset comparison | consistent method order, values visible, baselines neutral |
| line | trends over scale, time, threshold, training | marker and line dual encoding |
| heatmap | matrix, taxonomy, attention, error grid | continuous palette, cell values when useful |
| scatter | efficiency-effectiveness tradeoff | axes with units, meaningful quadrant |
| box plot | variance across seeds or samples | distribution not just mean |
| radar | multiple capability axes | use sparingly and keep axes interpretable |

Use code-generated plots for experiment results. Keep plot scripts versioned
and regenerate from recorded run artifacts.

## Universal Quality Gate

- vector final output when feasible: PDF, EPS, or SVG
- font readable after LaTeX scaling, normally at least 8 pt
- color-blind-safe palette and no color-only encoding
- honest axis ranges, labeled log scales, and error bars when supported
- self-contained labels and captions
- no 3D chart effects, decorative shadows, chartjunk, or misleading aspect
  ratios
- quantitative caption claims map to evidence

## AI-Assisted Figure Rule

AI image tools may help produce a rough conceptual sketch after the figure
contract is clear. They must not be treated as final scientific figures because
they cannot guarantee data accuracy, editable vector structure, typography,
consistent style, or correct entity labels.

For paper figures:

```text
paper logic
  -> figure contract
  -> rough sketch or prompt
  -> human/vector redraw or reproducible plot script
  -> caption evidence audit
```
