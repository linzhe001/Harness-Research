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
- keep changes architecture-faithful
- validate each generated Python file
- sync `project_map.json` after stable file creation or interface changes
