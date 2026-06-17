# Final Gate Ledger

- `decision`: USER_GATE
- `paper_id`: `surgical-ai-review`
- `reason`: Citation verification and empirical figure data remain incomplete; no local experiment is required.

| finding_id | decision | owning_phase | required_action | status |
| --- | --- | --- | --- | --- |
| gate_001 | USER_GATE | citation | Human/full-text confirmation for metadata-only or partial PDF-extracted references before publication. | open |
| gate_002 | USER_GATE | figure | Build dataset metadata CSV before rendering Figure 2 Panel A/C/D as empirical charts. | open |
| gate_003 | USER_GATE | figure | Provide cost/value data if Figure 1 should move from conceptual landscape to empirical coordinates. | open |
| gate_004 | COMPLETE | intake | PDF text extracted; source index established; figure scan executed. | done |
| gate_005 | COMPLETE | patch | Markdown review draft written with citation placeholders and figure/table placeholders. | done |
| gate_006 | NOT_RUN | run_request | No local experiment, baseline, ablation, or metric export required. | not_applicable |
| gate_007 | COMPLETE | harden | `artifact_check.py` passed with 0 errors and 0 warnings. | done |
| gate_008 | COMPLETE_WITH_WARNINGS | citation | `citation_bank_check.py` passed with 0 errors; warnings remain only for candidate inventory rows that intentionally have no direct support. | done |
| gate_009 | COMPLETE_WITH_USER_GATE | figure | Four editable SVG draft figures were created; empirical panels remain gated. | done |
