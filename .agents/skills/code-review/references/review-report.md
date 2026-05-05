# Code Review Report Format

## Report Directory

For medium and heavy reviews, write a local trace directory:

```text
.agents/state/review_traces/code-review/<YYYY-MM-DD>_runNN/
  run.meta.json
  codex_review.request.json
  codex_review.response.md
  codex_review.meta.json
  deepseek_review.request.json
  deepseek_review.response.md
  deepseek_review.meta.json
  review_report.md
```

The directory is local audit state and is not canonical project state.

## Required Git Snapshot

Record these fields in the report:

- `review_id`
- `generated_at`
- `mode`: `light`, `medium`, or `heavy`
- `repo_root`
- `branch`
- `head_commit`
- `base_ref`
- `base_commit`
- `scope_kind`: `working_tree`, `staged`, `commit_range`, or `path_set`
- `working_tree_status`
- `diff_commands`
- `changed_line_map_commands`
- `reviewers`
- `trace_dir`

Use these commands when applicable:

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git rev-parse --verify <base_ref>
git diff --name-status
git diff --unified=0 --no-ext-diff
git diff --cached --unified=0 --no-ext-diff
git diff --name-status <base_ref>...HEAD
git diff --unified=0 --no-ext-diff <base_ref>...HEAD
```

If a command is not applicable or cannot run, record `NOT_RUN` with the reason.

## Changed Line Map

Line references must come from the current checked-out files and diff hunks.
Use `git diff --unified=0` hunk headers:

```text
@@ -<old_start>,<old_count> +<new_start>,<new_count> @@
```

Report line ranges as:

- `path:new_start-new_end` for added or modified lines
- `path:old_start-old_end (deleted)` for deleted-only findings
- `path:line` for single-line findings

Every accepted `critical` or `warning` finding must include a file path and line
reference. If a reviewer gives a broad concern without a line reference, mark it
`needs_human` or `rejected_with_reason` until it is verified.

## Markdown Template

```markdown
# Code Review Report

## Review Metadata

| Field | Value |
|---|---|
| review_id |  |
| generated_at |  |
| mode |  |
| repo_root |  |
| branch |  |
| head_commit |  |
| base_ref |  |
| base_commit |  |
| scope_kind |  |
| working_tree_status |  |
| trace_dir |  |

## Scope

| File | Status | Changed Lines | Source | Notes |
|---|---|---:|---|---|
|  |  |  |  |  |

## Commands

| Command | Result | Reason | Artifact |
|---|---|---|---|
|  |  |  |  |

## Reviewer Artifacts

| Reviewer | Model | Status | Trace | Notes |
|---|---|---|---|---|
| codex |  | used/NOT_RUN |  |  |
| deepseek | deepseek-v4-pro | used/NOT_RUN |  |  |

## Findings

| ID | Severity | Confidence | Source | Status | Location | Summary | Evidence | Recommendation |
|---|---|---|---|---|---|---|---|---|
| CR-001 | critical/warning/info | high/medium/low | codex/deepseek/self | accepted/rejected_with_reason/needs_human/not_reproducible | path:line |  |  |  |

## Reconciliation

- `accepted_critical`:
- `accepted_warning`:
- `accepted_info`:
- `rejected_with_reason`:
- `needs_human`:
- `not_reproducible`:

## Residual Risk

- 

## Gate Ledger

| Gate | Command | Result | Reason | Artifacts |
|---|---|---|---|---|
| git_metadata_snapshot |  |  |  |  |
| changed_line_map |  |  |  |  |
| codex_review_or_NOT_RUN |  |  |  |  |
| deepseek_review_or_NOT_RUN |  |  |  |  |
| reconcile_review_findings |  |  |  |  |
| write_review_report_or_NOT_RUN |  |  |  |  |
```

## Verdict Rules

- `PASS`: no accepted critical or warning findings in scope.
- `REVIEW`: unresolved warning or `needs_human` item remains.
- `FAIL`: at least one accepted critical finding remains.

Heavy review cannot return `PASS` while Codex or DeepSeek is unavailable unless
the report explains why the missing reviewer was `NOT_RUN` and what compensating
local checks were performed.
