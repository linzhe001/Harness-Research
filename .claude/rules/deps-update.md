---
description: Remind user to refresh CLAUDE.md Environment section after dependency file changes
globs:
 - "requirements*.txt"
 - "environment*.yml"
 - "pyproject.toml"
 - "setup.py"
 - "setup.cfg"
---

# Dependency File Change Reminder

When any dependency specification file is modified (`requirements*.txt`, `environment*.yml`, `pyproject.toml`, `setup.py`), remind the user to run `/env-setup refresh` to sync the `## Environment` section of CLAUDE.md with the updated dependencies.
