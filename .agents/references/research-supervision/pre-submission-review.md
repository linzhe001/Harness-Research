# Pre-Submission Review Asset

## Purpose

Use this asset for manuscript hardening, paper review, `auto-paper-harden`, and
final claim checks. It turns writing advice into an audit that produces
prioritized findings.

## Severity

| Severity | Meaning | Action |
|---|---|---|
| `CRITICAL` | blocks submission, central claim, or reproducibility | fix before submit |
| `MAJOR` | likely reviewer complaint or credibility risk | fix unless explicitly accepted |
| `MINOR` | polish, readability, or formatting issue | fix when time permits |

## Five-Dimension Audit

| Dimension | Blocking question |
|---|---|
| Macro logic | Does the story chain hold from motivation to experiments? |
| Writing detail | Does each paragraph have one job, a topic sentence, and transitions? |
| Grammar/wording | Are sentences precise, simple, and free of repeated mechanical errors? |
| Format/LaTeX | Are citations, labels, equations, floats, and venue constraints correct? |
| Figure quality | Are figures legible, honest, vector-ready, and caption-supported? |

## Macro Logic Checks

- The introduction follows the correct skeleton for the paper type.
- Limitations motivate challenges or research questions.
- Challenges map to method modules or benchmark design choices.
- Contributions map to sections and evidence.
- Experiments evaluate the stated claims.
- Related work is fair and consistent with the claimed gap.
- Limitations do not contradict the main claim.

Failure patterns:

| Pattern | Severity |
|---|---|
| missing central experiment or unsupported main claim | `CRITICAL` |
| contribution has no delivering section | `CRITICAL` |
| running example abandoned after introduction | `MAJOR` |
| module names differ across intro, method, figure, and code | `MAJOR` |
| related work contradicts the gap framing | `MAJOR` |

## Writing Detail Checks

- Every paragraph opens with its point.
- Paragraphs are neither one-line fragments nor multi-topic blocks.
- Leading text introduces dense lists, algorithms, and figures.
- Claims use specific nouns, metrics, and scope.
- The prose does not force the reader to infer the logic chain.

Avoid AI-tone inflation such as "revolutionary", "unprecedented",
"transformative", "pave the way", and unsupported "state-of-the-art" claims.
Avoid semantic dashes as sentence connectors in paper prose.

## Grammar And Wording Checks

- articles for singular countable nouns
- subject-verb agreement
- tense: present for method and paper claims, past for completed experiments
- one main idea per sentence
- no ungrounded translation artifacts
- terms defined once and used consistently

Use grammar tools as mechanical support only; they do not validate claims.

## LaTeX And Format Checks

- central macros exist for system names and repeated terms
- file structure separates sections, figures, experiments, algorithms, and
  response files when applicable
- citations and references use non-breaking spaces where required
- labels use prefixes such as `fig:`, `tab:`, `sec:`, `eq:` and avoid spaces
- figures are vector-ready or explicitly justified
- equations define symbols before use
- floats obey venue constraints
- response/revision files map each reviewer comment to edits

## Figure Checks

- Every figure has a role and claim.
- Captions state the finding first, then setup and boundary.
- Quantitative claims map to run artifacts or citation rows.
- Axis ranges, scales, and error bars are honest.
- Font, color, legend, and labels remain readable after scaling.

## Reviewer-Value Checklist

- Novel Problem: useful and clearly defined.
- Novel Method: more than a simple combination.
- Nice Story: logic is easy to follow.
- Nice Presentation: figures, layout, grammar, and formatting are professional.
- Strong Experiments: baselines are current, settings fair, controls adequate.

If a central item is missing, return `RUN_REQUEST`, `USER_GATE`, or route back
to the owning writing phase instead of polishing around the problem.
