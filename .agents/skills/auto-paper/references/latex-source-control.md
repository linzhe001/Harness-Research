# LaTeX Source Control

## Preservation Rules

Preserve existing LaTeX structure unless the patch plan explicitly says
otherwise:

- `\label`, `\ref`, `\autoref`, `\Cref`
- `\cite`, `\citep`, `\citet`, and existing citation keys
- `\begin` and `\end` environments
- figure and table paths
- equations and math macros
- template macros and venue-specific commands
- review/final wrapper files

## Patch Granularity

Patch one section or one contiguous group of `unit_id` rows at a time. In a
guarded Harness workspace, default to generating `latex_patch.diff` or
`patches/<unit_id>.diff` under `auto_paper_output/<paper_id>/`. Direct source
edits require explicit operator authorization and a write scope that permits
the target paper path.

Record a line anchor, file path, rationale row, patch artifact, affected claim
IDs, affected citation IDs, and guard result in `patch_ledger.md`.

## Bib Policy

Do not add a citation key unless it appears in `citation_support_bank.md`. Do
not delete a key that still supports a registered claim. New `.bib` entries
must be covered by citation audit.

## Guard Report

Each patch should run a static LaTeX guard on an applied temporary copy and,
when configured, a compile command. Report `PASS`, `FAIL`, or `NOT_RUN` with
the command, reason, and artifact path.
