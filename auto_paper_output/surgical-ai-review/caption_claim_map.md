# Caption Claim Map

| figure_id | caption_claim | claim_id | support_source | support_grade | allowed_wording | risk_note |
| --- | --- | --- | --- | --- | --- | --- |
| fig_001 | Surgical AI adoption should be interpreted through both clinical value and cost/scalability constraints. | claim_001 | Kawka2023; Marcus2024; Sadri2023; Lai2024; Bosscha2026 | strong plus partial plus limiting | "该图是价值评估框架，而非现有系统确定排名。" | Numeric placement requires empirical data. |
| fig_001 | Hardware-agnostic AI navigation belongs in a hypothesized target zone, not an already proven quadrant. | claim_006 | Carstens2026; Mascagni2024 | limiting | "虚线区域表示本文提出的目标区域，尚需临床和成本证据验证。" | Avoid promotional caption. |
| fig_002 | SSU research shows concentration and validation gaps. | claim_002 | Carstens2026 | strong | "系统综述层面已有单中心、术式集中和外部验证不足证据。" | Exact percentages need full-text check. |
| fig_002 | Dataset geography, institution count, and diversity scoring require manual dataset metadata extraction. | claim_007 | EndoVis; CAMMA_datasets; Endoscapes2025; Cholec80CVS2023 | metadata_only plus strong dataset examples | "Panel A/C/D 为待编码实证面板。" | USER_GATE; do not draw final map from memory. |
| fig_003 | Existing 3D and video models occupy layers of a larger spatial-world-model landscape. | claim_004 | EndoNeRF2022; Deform3DGS2024; EndoFM2023; SurgVISTA2026; EndoMamba2025; EndoDAC2024; Endo3R2025 | partial | "这些方法展示了组件级能力，而非完整临床导航系统。" | Central overclaim risk. |
| fig_003 | DUSt3R, VGGT, and CUT3R are non-surgical inspirations for geometry and persistent state. | claim_004 | DUSt3R2024; VGGT2025; CUT3R2025 | background | "通用 3D foundation models 提供启发，但仍需手术场景适配。" | Must not imply surgical validation. |
| fig_004 | LC is a practical semantic safety-assistance and data-flywheel entry point. | claim_005 | Mascagni2024; Cholec80CVS2023; Endoscapes2025 | strong | "LC 是入口，不是完整三维导航终点。" | Avoid linear "LC to all surgery" claim. |
| fig_004 | Strong preoperative-imaging procedures are candidate validation fields for deformable 3D navigation. | claim_005 | Dai2025; Sommer2024 | partial | "肝、肾、胰、前列腺等场景更适合检验术前-术中三维配准导航。" | Representative, not exhaustive. |
| table_001 | The evidence ledger separates direct support, partial support, limiting evidence, and USER_GATE rows. | claim_006; claim_007 | citation_support_bank.md | mixed | "表中 support grade 不等同于全文事实强度，metadata_only 行不作为主张支撑。" | Prevent citation laundering from PDF. |
