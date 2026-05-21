from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from harness_contracts import load_contracts, repo_root


def _frontmatter_description(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    for line in parts[1].splitlines():
        if line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            return value.strip('"').strip("'")
    return ""


def _list_items(values: list[str]) -> str:
    if not values:
        return "- none"
    return "\n".join(f"- `{value}`" for value in values)


def _read_paths(contract: dict[str, Any]) -> list[str]:
    read_set = contract.get("required_read_set", {})
    paths: list[str] = []
    for section in ("harness", "skill", "project_when_present", "project_optional"):
        values = read_set.get(section, [])
        if isinstance(values, list):
            paths.extend(str(value) for value in values)
    return list(dict.fromkeys(paths))


def _write_paths(contract: dict[str, Any]) -> list[str]:
    scope = contract.get("write_scope", {})
    if not isinstance(scope, dict):
        return []
    values = scope.get("allowed_paths", [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def _artifact_outputs(
    contract: dict[str, Any],
    *,
    final: bool | None = None,
    requires_tool: bool | None = None,
) -> list[str]:
    values = contract.get("artifact_outputs", [])
    if not isinstance(values, list):
        return []
    rendered: list[str] = []
    for output in values:
        if not isinstance(output, dict):
            continue
        if final is not None and bool(output.get("is_final")) is not final:
            continue
        if (
            requires_tool is not None
            and bool(output.get("requires_tool")) is not requires_tool
        ):
            continue
        kind = output.get("kind", "unknown")
        paths = output.get("paths", [])
        if not isinstance(paths, list):
            continue
        suffix = ""
        replacement = output.get("replacement")
        if replacement:
            suffix = f" -> `{replacement}`"
        for path in paths:
            rendered.append(f"{kind}: {path}{suffix}")
    return rendered


def _first_values(values: list[Any], limit: int = 8) -> list[str]:
    return [str(value) for value in values[:limit]]


def render_stage_cards(root: Path) -> str:
    contracts = load_contracts(root)
    lines: list[str] = [
        "# Harness Workflow Stage Cards",
        "",
        (
            "本文件由 `schemas/skill_contracts.json` 生成, "
            "用作 operator 快速阅读入口。"
        ),
        "contract 仍是权限和 gate 的 source of truth。",
        "",
        "生成命令:",
        "",
        "```bash",
        (
            "python tooling/codex_hooks/generate_stage_cards.py "
            "--workspace-root . --output workflow_handbook/Workflow_Stage_Cards.md"
        ),
        "```",
        "",
        "通用读法:",
        "",
        "```text",
        (
            "Stage -> Purpose -> Inputs -> Can write -> Must read "
            "-> Must prove -> Cannot do -> Exit condition"
        ),
        "```",
        "",
    ]
    for contract in contracts:
        skill = str(contract.get("skill", "<unknown>"))
        skill_file = root / ".agents" / "skills" / skill / "SKILL.md"
        description = _frontmatter_description(skill_file) or "See the skill file."
        triggers = _first_values(contract.get("triggers", []), limit=8)
        required_actions = _first_values(contract.get("required_actions", []), limit=12)
        gate_conditions = _first_values(
            contract.get("gate_ledger_required_when", []), limit=12
        )
        forbidden_actions = _first_values(
            contract.get("forbidden_actions", []), limit=12
        )
        lines.extend(
            [
                f"## {skill}",
                "",
                f"Purpose: {description}",
                "",
                "Inputs / triggers:",
                _list_items(triggers),
                "",
                "Can write:",
                _list_items(_write_paths(contract)),
                "",
                "Final outputs:",
                _list_items(_artifact_outputs(contract, final=True)),
                "",
                "Tool-owned outputs:",
                _list_items(_artifact_outputs(contract, requires_tool=True)),
                "",
                "Must read:",
                _list_items(_read_paths(contract)),
                "",
                "Must prove:",
                _list_items(required_actions + gate_conditions),
                "",
                "Cannot do:",
                _list_items(forbidden_actions),
                "",
                "Exit condition:",
                (
                    "- Required reads are complete before writes; writes stay inside "
                    "`write_scope.allowed_paths`; Gate ledger reports command, "
                    "result, reason, and artifacts when gate conditions are touched."
                ),
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate operator-readable Harness workflow stage cards."
    )
    parser.add_argument(
        "--workspace-root", default=".", help="Repository root or subdirectory."
    )
    parser.add_argument(
        "--output",
        help="Write generated Markdown to this path. Omit to print to stdout.",
    )
    args = parser.parse_args()

    root = repo_root(Path(args.workspace_root))
    rendered = render_stage_cards(root)
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
