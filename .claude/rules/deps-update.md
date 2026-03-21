---
description: 依赖文件变更后提醒用户刷新 CLAUDE.md 的 Environment 部分
globs:
 - "requirements*.txt"
 - "environment*.yml"
 - "pyproject.toml"
 - "setup.py"
 - "setup.cfg"
---

# Dependency File Change Reminder

When any dependency specification file is modified (`requirements*.txt`, `environment*.yml`, `pyproject.toml`, `setup.py`), remind the user to run `/env-setup refresh` to sync the `## Environment` section of CLAUDE.md with the updated dependencies.
