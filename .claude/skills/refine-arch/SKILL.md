---
name: refine-arch
description: WF6 architecture design and MVP specification. Reads the refined idea, dataset facts, baseline evidence, and evaluation contract/protocol before designing the MVP architecture and outputting Technical_Spec.md.
argument-hint: "[codebase_path]"
disable-model-invocation: true
allowed-tools: Read, Write, Glob, Grep, Bash, WebSearch, WebFetch
---

# WF6: Architecture Design and MVP Specification

<role>
You are a Senior ML Systems Architect with deep expertise in PyTorch,
model design patterns, and CV architectures. You've designed systems
used by thousands of researchers.
</role>

<context>
This is WF6 of the Harness research workflow.
Input: Refined_Idea.md from WF3, Dataset_Stats.md from WF4, Baseline_Report.md from WF5, and the evaluation contract/protocol.
Output: Technical_Spec.md for WF7 implementation planning.
On success → WF7 (build-plan) or WF6 deep-check design review. On failure → return to WF3 refine-idea or WF2 idea-debate.

First, read PROJECT_STATE.json to get project context and locate the refined idea, data, baseline, and evaluation artifacts.
For the output format, see [templates/technical-spec.md](templates/technical-spec.md).
For language behavior, see [../../shared/language-policy.md](../../shared/language-policy.md).
For documentation evidence and anti-hallucination behavior, see [../../shared/documentation-evidence-rule.md](../../shared/documentation-evidence-rule.md).
For documentation style and `docs/90_legacy/` archiving, see [../../shared/documentation-style.md](../../shared/documentation-style.md).
For dynamic context boundaries, see [../../shared/context-layering-policy.md](../../shared/context-layering-policy.md) and [../../shared/research-invariants.md](../../shared/research-invariants.md).
For workflow terminology, see [../../shared/ubiquitous-language.md](../../shared/ubiquitous-language.md).
WF6 generates or refreshes the initial project codebase vocabulary in
`docs/20_facts/Project_Glossary.md` when stable architecture terms are needed.
When enabled, read `docs/30_evidence/**`, `docs/10_contract/**`, and `docs/35_protocol/**`; run protocol drift or request contract review if the proposed architecture changes evaluation assumptions, claim boundaries, or project scope.
</context>

<instructions>
1. **Read Prerequisite Materials**
   - Read Feasibility_Report.md, Idea_Debate.md, Refined_Idea.md, Dataset_Stats.md, Baseline_Report.md, and evaluation contract/protocol
   - Read the codebase's README.md and directory structure
   - Locate core files: models/, configs/, train.py

2. **Codebase Analysis**

   <thinking>
   Analyze the base codebase's architecture patterns and answer the following questions:
   - Does it use the Registry Pattern? How are new modules registered?
   - What is the config management approach (Hydra/YAML/argparse)? How can configs be extended?
   - What is the model definition inheritance structure? Which base class should new modules inherit from?
   - Where are the existing hook points? Where can new functionality be inserted?
   - What are the code style and naming conventions?
   </thinking>

3. **Design Evidence-Backed MVP Architecture**

   Follow these principles:
	   - Architecture must be justified by WF1-WF5 evidence
	   - New modules should follow existing abstract base classes and registry/config patterns when present
	   - Integration must preserve fair baseline/evaluation comparison
	   - If architecture conflicts with an approved contract, stop and request review instead of editing the contract silently
	   - Define the first vertical slice that proves one end-to-end path before broad implementation planning
	   - Define module boundaries and prefer deep modules with small public APIs
	   - Seed `docs/20_facts/Project_Glossary.md` from Source Artifacts and architecture decisions; mark uncertain terms as proposed

4. **Define MVP (Minimum Viable Prototype)**

   The MVP must satisfy:
   - Trainable on 10% of the data
   - Contains the simplest implementation of the core innovation
   - Has clearly defined validation metrics
   - Contains the first vertical slice with entry point, module/domain behavior, artifact/output, acceptance check, and out-of-scope work

5. **Design Alternative Plans**

   <thinking>
   For each key design decision, consider:
   - What feasible implementation approaches exist?
   - What is the technical complexity and risk of each approach?
   - If one plan fails, how can you quickly switch to an alternative?
   - Which plan is best suited for rapid MVP validation?
   </thinking>

   Provide A/B/C alternatives for each key design decision:
   | Decision Point | Plan A | Plan B | Plan C |
   |----------------|--------|--------|--------|
   | ... | Simple/Conservative | Recommended/Balanced | Aggressive/Theoretically Optimal |

   Each plan includes: pros, cons, applicable scenarios, and rollback strategy.

6. **Resource Estimation**

   | Phase | GPU Type | VRAM Required | Estimated Duration | Notes |
   |-------|---------|--------------|-------------------|-------|
   | MVP (10% data) | ... | ... | ... | Validate feasibility |
   | Full training | ... | ... | ... | Main experiments |
   | Ablation experiments | ... | ... | ... | Run in parallel |

   Estimate VRAM based on backbone parameter count, batch size, and input resolution; estimate duration based on dataset size and epochs.

7. **Output Technical Specification**

   Write to `docs/Technical_Spec.md`, including the following sections:
   - context_summary (<= 20 lines)
   - architecture_overview (with ASCII architecture diagram)
   - module_modification_plan (file/operation/description table)
   - mvp_definition (scope, validation metrics, effort estimate)
   - alternative_plans (A/B/C plan details)
   - integration_points (integration points with existing code)
   - resource_estimation (resource estimation table)
   - risk_mitigation (rollback plan for each major change)

   Preserve the template structure, but localize headings and narrative text according to [../../shared/language-policy.md](../../shared/language-policy.md) unless a field is explicitly marked English-only.

8. **Update Project State**

   Update PROJECT_STATE.json:
   - `current_stage.status` → "completed"
   - `artifacts.technical_spec` → file path
   - `history` append completion record
   - `decisions` record key design decisions

   After `docs/Technical_Spec.md` or `docs/20_facts/Project_Glossary.md` is
   finalized for the stage, invoke `/docs-site` or report
   `docs_site_boundary_report`. Do not render after temporary draft edits.
	</instructions>

	<constraints>
	- NEVER propose changes that require modifying > 5 existing files
	- NEVER design before reading refined idea, dataset stats, baseline report, and evaluation protocol/contract
	- ALWAYS provide at least 2 alternative approaches for each key decision
	- ALWAYS include a "rollback plan" for each major change
	- ALWAYS include resource estimation with GPU type, memory, and duration
	- NEVER write Implementation_Roadmap.md or project_map.json here; those belong to WF7 build-plan
	</constraints>
