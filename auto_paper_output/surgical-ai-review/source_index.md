# Source Index

- `paper_id`: `surgical-ai-review`
- Intake mode: build from PDF material and verified-reference plan
- Indexed items: 31
- Source caveat: `手术AI文献调研.pdf` is an AI dialogue/history PDF. Its cited literature is treated as candidate metadata until separately verified.

| Source ID | Type | Title/Name | Path | Why Included | Used For |
| --- | --- | --- | --- | --- | --- |
| src_pdf_001 | PDF | 手术AI文献调研 | `手术AI文献调研.pdf` | Primary user-provided source material | Intake, topic, structure, candidate citations, figure cues |
| src_text_001 | extracted_text | Extracted PDF text | `auto_paper_output/surgical-ai-review/source_pdf_text.txt` | `pdftotext -layout` extraction from `src_pdf_001` | Searchable source for claims, methods, figures, tables |
| src_scan_001 | generated_artifact | Figure requirement scan | `auto_paper_output/surgical-ai-review/figure_requirement_scan.md` | Script-detected figure/table cues from PDF/text | Figure branch requirements |
| src_web_001 | verified_reference | Kawka et al. 2023, robotic vs laparoscopic RCT systematic review | `https://pubmed.ncbi.nlm.nih.gov/37442833/` | Verifies metadata for value/cost claim | Citation support for value constraint |
| src_web_002 | verified_reference | Sadri et al. 2023, full economic evaluations of robotic-assisted surgery | `https://pmc.ncbi.nlm.nih.gov/articles/PMC10678817/` | Verifies metadata and open article availability | Citation support for economic nuance |
| src_web_003 | verified_reference | Marcus et al. 2024, IDEAL framework for surgical robotics | `https://www.nature.com/articles/s41591-023-02732-7` | Verifies framework and evaluation scope | Citation support for evaluation boundary |
| src_web_004 | verified_reference | Lai et al. 2024, economic evaluations of robotic-assisted surgery | `https://pubmed.ncbi.nlm.nih.gov/39333303/` | Verifies metadata for methods/challenges review | Citation support for dynamic cost-effectiveness caveat |
| src_web_005 | verified_reference | Bosscha et al. 2026, cost analyses in randomized trials on robot-assisted surgery | `https://academic.oup.com/bjsopen/article/10/1/zraf161/8442986` | Verifies metadata and cost-analysis quality focus | Citation support for incomplete cost evidence |
| src_web_006 | verified_reference | Carstens et al. 2026, AI for surgical scene understanding systematic review | `https://www.nature.com/articles/s41746-025-02227-4` | Verifies 188-study SSU review and reporting-quality focus | Citation support for data bottleneck |
| src_web_007 | verified_reference | Kiyasseh et al. 2023, bias in AI-based surgeon skill assessment | `https://www.nature.com/articles/s41746-023-00766-2` | Verifies bias/fairness reference | Citation support for fairness and distribution caveat |
| src_web_008 | verified_reference | Hashemi et al. 2023, acquisition and usage of robotic surgical data | `https://pmc.ncbi.nlm.nih.gov/articles/PMC10338401/` | Verifies da Vinci Si/Xi acquisition workflow | Citation support for robotic data engineering friction |
| src_web_009 | verified_reference | Protserov et al. 2024, operating room-ready AI | `https://www.nature.com/articles/s41746-024-01225-2` | Verifies OR-ready device-agnostic AI title and venue | Citation support for hardware-agnostic video entry |
| src_web_010 | verified_reference | Mascagni et al. 2024, early-stage AI assistance for LC | `https://pubmed.ncbi.nlm.nih.gov/37935636/` | Verifies SurgFlow/LC early-stage clinical evaluation metadata | Citation support for LC entry with maturity caveat |
| src_web_011 | verified_reference | Endoscapes dataset, Scientific Data 2025 | `https://pubmed.ncbi.nlm.nih.gov/40000637/` | Verifies 201-video LC dataset metadata | Citation support for LC dataset foundation |
| src_web_012 | verified_reference | Cholec80-CVS dataset, Scientific Data 2023 | `https://www.nature.com/articles/s41597-023-02073-7` | Verifies CVS annotation dataset metadata | Citation support for LC/CVS data foundation |
| src_web_013 | verified_reference | Sommer et al. 2024, intraoperative liver deformation and organ motion | `https://pubmed.ncbi.nlm.nih.gov/38148403` | Verifies liver deformation reference | Citation support for static prior limitation |
| src_web_014 | verified_reference | Dai et al. 2025, laparoscopic liver surface registration | `https://pubmed.ncbi.nlm.nih.gov/39739191/` | Verifies preoperative/intraoperative registration reference | Citation support for deformable 3D navigation validation field |
| src_web_015 | verified_reference | EndoNeRF, MICCAI 2022 | `https://conferences.miccai.org/2022/papers/353-Paper1091.html` | Verifies title and MICCAI page | Citation support for visible-surface neural rendering |
| src_web_016 | verified_reference | Deform3DGS, MICCAI 2024 | `https://papers.miccai.org/miccai-2024/206-Paper3887.html` | Verifies 3DGS surgical reconstruction reference | Citation support for fast visible-surface modeling |
| src_web_017 | verified_reference | Endo-FM, MICCAI 2023 | `https://conferences.miccai.org/2023/papers/283-Paper0676.html` | Verifies endoscopy foundation-model reference | Citation support for surgical video foundation models |
| src_web_018 | verified_reference | SurgVISTA, npj Digital Medicine 2026 | `https://www.nature.com/articles/s41746-026-02403-0` | Verifies video-level surgical pretraining reference | Citation support for spatiotemporal foundation model trend |
| src_web_019 | verified_reference | EndoDAC, MICCAI 2024/arXiv | `https://arxiv.org/abs/2405.08672` | Verifies endoscopic depth foundation adaptation reference | Citation support for depth/geometry adaptation bottleneck |
| src_web_020 | verified_reference | Endo3R, MICCAI 2025/arXiv | `https://papers.miccai.org/miccai-2025/0285-Paper0780.html` | Verifies online monocular surgical reconstruction reference | Citation support for geometry + memory direction |
| src_web_021 | verified_reference | DUSt3R, CVPR 2024/arXiv | `https://arxiv.org/abs/2312.14132` | Verifies pointmap-based general 3D vision reference | Citation support for general 3D foundation-model inspiration |
| src_web_022 | verified_reference | VGGT, CVPR 2025/project page | `https://vgg-t.github.io/` | Verifies feed-forward camera/pointmap/depth/track outputs | Citation support for general 3D foundation-model inspiration |
| src_web_023 | verified_reference | CUT3R, CVPR 2025/project page | `https://cut3r.github.io/` | Verifies persistent-state continuous 3D perception concept | Citation support for latent spatial memory analogy |
| src_web_024 | verified_reference | EndoMamba, MICCAI 2025 | `https://papers.miccai.org/miccai-2025/0293-Paper2130.html` | Verifies efficient endoscopic video foundation-model reference | Citation support for real-time video representation trend |
| src_web_025 | metadata_source | Endoscapes PhysioNet record | `https://physionet.org/content/endoscapes-2023/1.0.0/` | Confirms dataset availability and annotations | Figure 2 dataset plan |
| src_web_026 | metadata_source | CAMMA dataset page | `https://camma.unistra.fr/datasets/` | Candidate dataset inventory source | Figure 2 dataset metadata plan |
| src_web_027 | metadata_source | EndoVis challenge ecosystem | `https://endovis.org/` | Candidate public-dataset/challenge ecosystem | Figure 2 dataset metadata plan |
