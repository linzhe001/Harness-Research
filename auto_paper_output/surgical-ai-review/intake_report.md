# Intake Report

- `paper_id`: `surgical-ai-review`
- Workflow: `build_from_materials`
- Draft target: `auto_paper_output/surgical-ai-review/review_draft.md`
- Source PDF: `手术AI文献调研.pdf`
- Extracted text: `auto_paper_output/surgical-ai-review/source_pdf_text.txt`
- PDF extraction command: `pdftotext -layout '手术AI文献调研.pdf' auto_paper_output/surgical-ai-review/source_pdf_text.txt`
- Extracted text size: 3337 lines, 6139 whitespace-delimited tokens, 148458 bytes
- Figure scan command: `python .agents/skills/auto-paper/scripts/figure_requirement_scan.py --paper-id surgical-ai-review --artifact-dir auto_paper_output/surgical-ai-review --root . --max-candidates 200 '手术AI文献调研.pdf' auto_paper_output/surgical-ai-review/source_pdf_text.txt`
- Figure scan result: 85 candidate cues written to `figure_requirement_scan.md`

## Intake Interpretation

The PDF is a browser-exported AI dialogue/history document dated 2026-06-16. It contains a proposed review topic, candidate argument structure, figure planning notes, and many candidate references, methods, systems, and datasets. It is useful as a planning and extraction source, but not as verified literature evidence.

## Required Output Scope

The operator requested a Chinese citation-supported review article, not a blog. The target article title is:

`从机器人中心到空间模型中心：通用手术导航的趋势综述`

The article must include:

- citation placeholders or verified-reference plans for external facts;
- figure/table placeholders, titles, and caption drafts;
- a figure contract and caption-claim map;
- citation support artifacts with explicit verification status;
- a manifest and USER_GATE when citation verification or empirical figure data remain incomplete.

## Candidate Figure/Table Requirements Accepted

| item | required title | intake status | gate |
| --- | --- | --- | --- |
| Figure 1 | Clinical Value-Cost Landscape of Surgical AI and Navigation Systems | accepted as conceptual value-cost landscape | USER_GATE for numeric placement |
| Figure 2 | Dataset Concentration and Long-Tail Bias in Surgical AI | accepted as mixed empirical/conceptual four-panel figure | USER_GATE for dataset metadata CSV and manual coding |
| Figure 3 | Layer-wise Research Landscape for Surgical Spatial World Models | accepted as literature-landscape schematic | no local experiment needed |
| Figure 4 | Three-Lane Roadmap toward Hardware-Agnostic Surgical Spatial Intelligence | accepted as roadmap schematic with evidence-strength gradient | USER_GATE for timeline or adoption evidence if converted to empirical claim |
| Table 1 | Evidence Ledger linking value constraints, data bottlenecks, spatial-computing claims, and representative literature | accepted as manuscript table | USER_GATE for unresolved candidate references |

## USER_GATE

This writing pass can produce the review draft and artifact set, but it should return `USER_GATE` because:

- the PDF contains AI-generated citation suggestions that require human or bibliographic confirmation before submission;
- Figure 2 Panel A/C/D require a structured dataset metadata table before they can be drawn as empirical charts;
- Figure 1 uses a conceptual target-zone placement for hardware-agnostic AI navigation because large-scale clinical cost-effectiveness data for that system category were not found in the provided source set;
- article claims about clinical outcomes must remain cautious because current verified sources support feasibility, data limitations, and evaluation needs more strongly than broad patient-outcome improvements.

## RUN_REQUEST

No local experiment, model training, baseline, ablation, or metric export is required for the present writing task. `RUN_REQUEST` is not returned.
