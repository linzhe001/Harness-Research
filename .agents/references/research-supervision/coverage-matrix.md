# Research Supervision Coverage Matrix

## Purpose

This matrix records how local research-supervision material was absorbed into
Harness-native assets. It is a maintainer audit, not a pointer that target
research workflows should read the external reference tree.

Identity, affiliation, contact, credit, meeting-speaker, school, logo, and
personal example details were intentionally removed. Case studies are converted
into generic paper-logic patterns. Source PDFs and images are not copied into
Harness assets.

## Coverage

| Source group | Extracted concept | Internal destination | Status |
|---|---|---|---|
| `handbook/01_Preliminary/1.1_*` | paper-quality lens: Novel Problem, Novel Method, Nice Story, Nice Presentation, strong experiments | `phd-research-primer.md`, `pre-submission-review.md` | absorbed |
| `handbook/01_Preliminary/*.pdf` | end-to-end research path, direction/problem choice, abstract/intro/method/figure diagrams | `phd-research-primer.md`, `research-supervision-patterns.md` | absorbed as anonymized Markdown and ASCII diagrams |
| `handbook/02_Idea_Generation/2.1_*` | idea lifecycle, capability/resource matching, time-to-submission pressure | `idea-evaluation.md` | absorbed |
| `handbook/02_Idea_Generation/2.2_*` | Higher, Faster, Stronger, Cheaper, Broader idea axes and entry strategies | `idea-evaluation.md`, `research-supervision-patterns.md` | absorbed |
| `handbook/02_Idea_Generation/2.3_*` | paradigm-shift probes: first principles, ignored hard problems, technology cycle, important-question list | `idea-evaluation.md` | absorbed |
| `handbook/03_Paper_Writing/3.1_*`, `3.2_*`, `3.3_*` | abstract, six-paragraph introduction, technical-paper logic, running example, contribution mapping | `paper-writing-layouts.md`, `paper-and-figure-system.md` | absorbed |
| `handbook/03_Paper_Writing/3.4_*` | benchmark/evaluation paper structure, five pillars, RQ-driven experiments, construction pipeline, findings | `benchmark-evaluation-paper.md` | absorbed |
| `handbook/03_Paper_Writing/3.5_*` | submission writing checklist, grammar, LaTeX, banned AI-tone patterns, revision organization | `pre-submission-review.md`, `paper-writing-layouts.md` | absorbed |
| `handbook/04_Scientific_Plotting/*` | motivated example, solution overview, experiment charts, vector format, caption, color, axis rules | `scientific-plotting.md`, `paper-and-figure-system.md` | absorbed |
| `handbook/05_Vibe_Research/5.1_*` | commander posture, context discipline, small-step coding, AI-assisted figure/writing limits | `ai-assisted-research-workflow.md`, `scientific-plotting.md`, `pre-submission-review.md` | absorbed without personal/tool-promotion details |
| `handbook/05_Vibe_Research/5.2_*` | meeting takeaways about AI-assisted coding, figure workflow, and writing boundaries | `ai-assisted-research-workflow.md` | absorbed as anonymized process notes |
| `handbook/05_Vibe_Research/assets/**` | screenshots, example generated figures, tool UI, identity-bearing meeting image | not copied | not imported; replaced by text workflow and quality gates |
| `handbook/06_Case_Studies/*` | reusable intro/story patterns: technique paper, cross-domain method framing, new setting/problem framing | `case-patterns.md`, `paper-writing-layouts.md` | absorbed as generic patterns |
| `docs/en/handbook/**` | English mirror of the handbook concepts | same assets as the Chinese handbook rows | audited as source-equivalent mirror; no separate import needed |
| `assets/images/**` | example paper figures, flowcharts, overview images, teaser examples | `scientific-plotting.md`, `paper-and-figure-system.md`, `paper-writing-layouts.md` | absorbed as abstract figure roles, contracts, and ASCII/process patterns; images not copied |
| `plugins/phd-research/skills/idea-evaluator/**` | fatal flaws, lifecycle match, five-axis scoring, paradigm probes, integrity gate output | `idea-evaluation.md` | absorbed |
| `plugins/phd-research/skills/benchmark-paper-template/**` | benchmark gap analysis, design goals, pipeline, experiments, checklist | `benchmark-evaluation-paper.md` | absorbed |
| `plugins/phd-research/skills/figure-designer/**` | figure type identification, universal visual rules, tool matrix, caption and axis audit | `scientific-plotting.md` | absorbed |
| `plugins/phd-research/skills/intro-drafter/**` | introduction flow, paper-type positioning, running example, contribution audit | `paper-writing-layouts.md` | absorbed |
| `plugins/phd-research/skills/tech-paper-template/**` | technical-paper thinking template and consistency checks | `paper-writing-layouts.md` | absorbed |
| `plugins/phd-research/skills/pre-submission-reviewer/**` | macro logic, section guides, forbidden patterns, grammar, LaTeX rules | `pre-submission-review.md` | absorbed |
| `plugins/phd-research/skills/vibe-research-workflow/**` | AI-assisted coding/figure/writing red lines and workflows | `ai-assisted-research-workflow.md` | absorbed |
| root/plugin README, changelog, contribution docs | packaging, plugin usage, installation, repository-specific metadata | not copied | not imported; Harness has its own skill/routing system |
| `scripts/lint_skills.py`, `.git*`, `LICENSE`, `llms.txt` | repository maintenance, license, crawler/model index, and VCS metadata | not copied | not imported; unrelated to Harness workflow behavior |

## Not Imported

- Raw PDFs, images, screenshots, logos, and meeting overview images.
- Personal names, affiliations, emails, school names, credits, and speaker
  identifiers.
- Tool-specific installation screenshots and transient model/tool marketing.
- Paper-specific prose, case-study quotes, and benchmark claims as facts.

## Harness Routing

Use the assets as L1 process guidance:

```text
grill/change -> idea-evaluation
build/run/analyze -> experiment-and-build-canvas + ai-assisted-research-workflow
write/auto-paper -> paper-writing-layouts + benchmark-evaluation-paper
figure work -> scientific-plotting
final paper audit -> pre-submission-review
case reasoning -> case-patterns
```

Any target-project claim created from these patterns still needs current
Source Artifacts, Conclusion Evidence, Gate Evidence, or Approval Evidence.
