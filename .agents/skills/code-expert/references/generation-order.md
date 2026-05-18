# Code Expert Generation Order

Generate initial code in this order unless the roadmap gives a stricter dependency graph:

1. `src/utils/`
2. `src/models/`
3. `src/data/`
4. `src/losses/`
5. `scripts/`
6. `tests/`

Requirements:

- read `project_map.json` and `docs/Implementation_Roadmap.md` first
- read `docs/20_facts/Project_Glossary.md` when it exists
- choose one roadmap slice at a time; do not implement unrelated slices
- write or update the focused test/smoke check before implementation when practical
- after a slice is implemented, validated, and `project_map.json` is synced,
  commit that Commit Slice before starting the next independent slice
- keep changes architecture-faithful
- keep public APIs inside the slice trace unless the boundary change is explicit
- validate each generated Python file
- sync `project_map.json` after stable file creation or interface changes
