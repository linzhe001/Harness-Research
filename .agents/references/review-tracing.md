# Review Tracing Protocol

## Purpose

Persist review prompt/response records so a later agent can audit reviewer independence, resume follow-up, and understand why a gate passed or failed.

## Scope

Apply after every cross-model or secondary-agent call used for critique, code review, idea debate, experiment audit, claim validation, or patch gating.

## Trace Directory

Use a local runtime directory under the shared `.agents/state/` tree:

```text
.agents/state/review_traces/<skill-name>/<YYYY-MM-DD>_runNN/
  run.meta.json
  001-<purpose>.request.json
  001-<purpose>.response.md
  001-<purpose>.meta.json
```

This directory is not canonical project state. It is local audit data and should not be committed.

## Required Fields

`request.json` should include:

- `purpose`
- `timestamp`
- `reviewer`
- `files_referenced`
- `prompt`

`response.md` should contain the full reviewer response when policy allows full tracing.

`meta.json` should include:

- `purpose`
- `timestamp`
- `reviewer`
- `thread_id` or agent id when available
- `status`

## Trace Modes

- `full` by default: save prompt and response.
- `meta`: save metadata only when content is sensitive.
- `off`: disable tracing only when explicitly requested.

## Fallback

If a reviewer is unavailable, write a meta trace with `status="unavailable"` and record the local self-review as provisional.
