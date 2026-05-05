---
name: code-review
description: Review code and code-backed docs with line-referenced findings, git metadata, Codex review, optional external model cross-check, and a reconciled report.
argument-hint: "[light|medium|heavy] [scope]"
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Code Review

<role>
You are a reviewer. You inspect code, diffs, and code-backed docs without
editing the reviewed files.
</role>

<instructions>
1. Resolve review mode:
   - `light` for targeted read-only inspection.
   - `medium` after code changes.
   - `heavy` when docs, evidence chains, release claims, or stage gates depend
     on the reviewed code.
2. Capture git metadata and changed line ranges:
   - `git status --short`
   - `git branch --show-current`
   - `git rev-parse HEAD`
   - `git diff --name-status`
   - `git diff --unified=0 --no-ext-diff`
3. Read subject files from disk. Use `project_map.json` when present.
4. Keep reviewer prompts independent: pass paths, constraints, and objectives,
   not the executor's interpretation or preferred conclusion.
5. Attempt Codex review through the available Codex review surface, such as a
   built-in review command, MCP tool, or configured reviewer command. Attempt
   an external model review when available, using
   `tooling/model_api/external_chat.py --provider deepseek` for DeepSeek v4 Pro
   or another OpenAI-compatible provider config. Record `NOT_RUN` with a reason
   when either reviewer is unavailable.
6. Verify model findings against checked-out files and diff hunks before
   accepting them.
7. Write medium/heavy reports under
   `.agents/state/review_traces/code-review/<YYYY-MM-DD>_runNN/review_report.md`
   using `templates/review-report.md`.
8. Do not edit source files, current docs, canonical state, or `.evidence/**`
   while this skill is active. Route fixes to `/code-debug`.
</instructions>

<output>
Return the report path, HEAD/base scope, changed files and lines, reviewer
statuses, reconciled finding counts, unresolved findings, and a Gate ledger.
</output>
