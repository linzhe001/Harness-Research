# Case Pattern Asset

## Purpose

This asset extracts generic writing patterns from case-study analyses. It does
not import paper-specific claims, numbers, figures, or authorship details.

Use it when `write` or `auto-paper-*` needs to classify a paper story and pick
the right introduction and figure structure.

## Pattern A: Tight Technique Paper

Use when the task is known and the paper proposes a new mechanism.

```text
known task
  -> current methods split into two or three routes
  -> one route has a precise bottleneck
  -> key mechanism addresses that bottleneck
  -> method modules realize the mechanism
  -> main result plus ablations prove the mechanism matters
```

Signals:

- problem definition can be one sentence
- key idea is the main story carrier
- contributions focus on method, mechanism, and evidence
- Figure 1 can be a performance teaser or failure case
- overview figure explains the mechanism, not the whole field

Risks:

- shallow combination of known methods
- weak or stale baseline
- method modules not tied to a challenge

## Pattern B: Cross-Domain Method Framing

Use when the contribution transplants a mature idea from one field into a new
task family.

```text
target task family
  -> limitation of current local methods
  -> mature idea from another field
  -> adaptation challenge
  -> unified representation or workflow
  -> results across multiple tasks show transfer value
```

Signals:

- `Broader` is the dominant improvement axis
- related work must credit both source and target domains
- challenge is not the source idea itself, but adapting it responsibly
- case studies should show why the transplant changes behavior

Risks:

- source-domain idea already used in a close setting
- paper overclaims generality from narrow task coverage
- overview figure hides adaptation details

## Pattern C: New Problem Or Setting

Use when the problem definition or setting is itself the contribution.

```text
real-world change or ignored hard case
  -> existing problem framing no longer fits
  -> new goal or task definition
  -> constraints and evaluation needs
  -> system, method, or benchmark to instantiate the setting
  -> experiments characterize the setting and support feasibility
```

Signals:

- P3 of the introduction is load-bearing
- contributions include problem formulation or setting
- motivated example is essential
- experiments characterize behavior, not only beat baselines

Risks:

- new setting is not important enough
- no measurable protocol
- claim boundary is too broad for the evidence

## Pattern D: Benchmark Or Evaluation Paper

Use when the paper's main value is a missing evaluation dimension.

```text
evaluation blind spot
  -> concrete failure case
  -> design goals
  -> construction pipeline
  -> evaluation framework
  -> findings and research opportunities
```

Use `benchmark-evaluation-paper.md` for the full design and writing checks.

## Harness Use

- `grill`: identify which pattern fits before readiness.
- `run` / `analyze`: record which future paper claim a result supports.
- `write`: choose the skeleton and figure roles.
- `auto-paper-argument`: keep claim register aligned with the pattern.
