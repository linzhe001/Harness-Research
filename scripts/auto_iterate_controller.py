#!/usr/bin/env python3
"""Thin import shim for the auto-iterate controller.

The real implementation lives in ``auto_iterate/controller.py``.
This file exists so that ``scripts/auto_iterate_controller.py`` can be
referenced as a standalone entry point if needed.
"""

from auto_iterate.controller import LoopController  # noqa: F401
