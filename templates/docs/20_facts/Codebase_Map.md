# Codebase Map

Status: draft
Evidence chain: N/A
Evidence audit: N/A
Audit result: N/A

## Current Answer

Summarize the current stable codebase structure after WF7 planning and after
each stable implementation change. Keep this document synchronized with
`project_map.json`.

## Stable Files

| Path | Responsibility | Public Interfaces | Entry Points | Maintenance Owner | Source Artifact |
| --- | --- | --- | --- | --- | --- |
| `src/example.py` |  |  |  | `$build-plan` / `$code-expert` / `$code-debug` |  |

## Entry Points

| Command or Path | Purpose | Inputs | Outputs | Validation Command |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Module Boundaries

| Module | Owns | Must Not Own | Depends On | Used By |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Public Interfaces

| Interface | Defined In | Called By | Contract or Shape | Change Rule |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## Update Rules

- Update this file in the same Commit Slice as `project_map.json` when stable
  file presence, responsibilities, entry points, public interfaces, config
  schema, tensor shapes, or dependency direction changes.
- Do not record volatile experiment outputs, temporary notebooks, caches, or
  run artifacts here.
- Mark uncertain ownership or interface facts as open questions instead of
  inventing stable facts.

## Open Questions

- [U:codebase_map.open] Fill with missing ownership, boundary, or interface facts.
