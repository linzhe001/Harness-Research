from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from harness_contracts import load_contracts, repo_root

STAGE_SPECS = [
    ("WF0", "wf0_init", "WF0 Init", "init-project"),
    ("WF1", "wf1_survey_idea", "WF1 Survey Idea", "survey-idea"),
    ("WF2", "wf2_idea_debate", "WF2 Idea Debate", "idea-debate"),
    ("WF3", "wf3_refine_idea", "WF3 Refine Idea", "refine-idea"),
    ("WF4", "wf4_data_prep", "WF4 Data Prep", "data-prep"),
    ("WF5", "wf5_baseline_repro", "WF5 Baseline Repro", "baseline-repro"),
    ("WF6", "wf6_refine_arch", "WF6 Refine Arch", "refine-arch"),
    ("WF7", "wf7_build_plan", "WF7 Build Plan", "build-plan"),
    ("WF8", "wf8_code_expert", "WF8 Code Expert", "code-expert"),
    ("WF9", "wf9_validate_run", "WF9 Validate Run", "validate-run"),
    ("WF10", "wf10_iterate", "WF10 Iterate", "iterate"),
    ("WF11", "wf11_final_exp", "WF11 Final Exp", "final-exp"),
    ("WF12", "wf12_release", "WF12 Release", "release"),
]

STAGE_GROUPS = [
    (
        "Explore",
        "WF0-WF4: turn an initial idea into scoped direction and data facts.",
        ["WF0", "WF1", "WF2", "WF3", "WF4"],
    ),
    (
        "Contract & Plan",
        "WF5-WF7: establish baseline, approved boundaries, architecture, and slices.",
        ["WF5", "WF6", "WF7"],
    ),
    (
        "Build & Validate",
        "WF8-WF9: implement a bounded slice and validate it with Gate Evidence.",
        ["WF8", "WF9"],
    ),
    (
        "Iterate & Release",
        "WF10-WF12: run iterations, final experiment checks, and release packaging.",
        ["WF10", "WF11", "WF12"],
    ),
]

STAGE_GUIDANCE = {
    "WF0": {
        "intent": "Initialize or refresh the workspace guidance and workflow state.",
        "start": (
            "`$init-project` for guidance setup, or `$orchestrator` for "
            "state checks."
        ),
        "effect": (
            "`AGENTS.md`, `CLAUDE.md`, `PROJECT_STATE.json`, and optional "
            "scaffold are ready."
        ),
    },
    "WF1": {
        "intent": (
            "Collect early Conclusion Evidence and decide whether the idea is "
            "worth pursuing."
        ),
        "start": "`$survey-idea` with the research idea and constraints.",
        "effect": (
            "`docs/Feasibility_Report.md` and evidence tables summarize "
            "viability and open questions."
        ),
    },
    "WF2": {
        "intent": (
            "Compare candidate directions and choose the strongest research path."
        ),
        "start": "`$idea-debate` after WF1 has enough evidence to compare options.",
        "effect": (
            "`docs/Idea_Debate.md` records the selected direction, alternatives, "
            "and risks."
        ),
    },
    "WF3": {
        "intent": (
            "Turn the selected idea into a tighter research question and "
            "execution target."
        ),
        "start": (
            "`$refine-idea` with the selected direction and unresolved "
            "assumptions."
        ),
        "effect": (
            "`docs/Refined_Idea.md` defines scope, hypothesis, and known "
            "unknowns."
        ),
    },
    "WF4": {
        "intent": (
            "Make data facts explicit before baseline or architecture work starts."
        ),
        "start": (
            "`$data-prep` after the dataset path and intended evaluation "
            "surface are known."
        ),
        "effect": (
            "Dataset stats, data facts, configs, and evidence tables are current."
        ),
    },
    "WF5": {
        "intent": (
            "Reproduce or establish a baseline and prepare approval-facing "
            "contracts."
        ),
        "start": "`$baseline-repro` after data facts and baseline target are clear.",
        "effect": (
            "Baseline report, baseline evidence, and draft or approved contracts "
            "are ready for later gates."
        ),
    },
    "WF6": {
        "intent": "Refine the technical architecture within approved boundaries.",
        "start": "`$refine-arch` after baseline and contract boundaries are available.",
        "effect": (
            "`docs/Technical_Spec.md` and glossary updates define the "
            "implementation shape."
        ),
    },
    "WF7": {
        "intent": "Convert the architecture into bounded implementation slices.",
        "start": "`$build-plan` after the technical spec is stable enough to slice.",
        "effect": (
            "`docs/Implementation_Roadmap.md`, `project_map.json`, and "
            "codebase map guidance align."
        ),
    },
    "WF8": {
        "intent": "Implement one bounded code slice under the current plan.",
        "start": (
            "`$code-expert` for first-pass planned work, or `$code-debug` "
            "for fixes."
        ),
        "effect": (
            "Changed code, focused validation, and map updates are ready "
            "for review."
        ),
    },
    "WF9": {
        "intent": "Validate the implementation before structured iteration.",
        "start": "`$validate-run` with the acceptance commands and expected behavior.",
        "effect": (
            "`docs/Validate_Run_Report.md` records PASS, REVIEW, or FAIL "
            "with Gate Evidence."
        ),
    },
    "WF10": {
        "intent": (
            "Run the Ralph-style loop: plan, code, run, evaluate, and decide "
            "the next round."
        ),
        "start": "`$iterate plan`, `$iterate run`, and `$iterate eval`.",
        "effect": (
            "`iteration_log.json` and `docs/40_iterations/**` capture runs, "
            "lessons, and decisions."
        ),
    },
    "WF11": {
        "intent": (
            "Run final experiment checks against approved contracts and "
            "claim boundaries."
        ),
        "start": "`$final-exp` after WF10 evidence supports a final evaluation.",
        "effect": (
            "`docs/Final_Experiment_Matrix.md` records the final experiment "
            "plan and gate result."
        ),
    },
    "WF12": {
        "intent": (
            "Prepare release artifacts while keeping claims inside the approved "
            "boundary."
        ),
        "start": "`$release` after WF11 and release readiness gates are satisfied.",
        "effect": (
            "`submission/**`, release docs, and final Gate Evidence are ready "
            "for explicit submit approval."
        ),
    },
}


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


def _reference_items(values: list[str]) -> str:
    if not values:
        return "- none"
    return "\n".join(f"- [[{value}]]" for value in values)


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
            suffix = f" -> {replacement}"
        for path in paths:
            rendered.append(f"{kind}: {path}{suffix}")
    return rendered


def _first_values(values: list[Any], limit: int = 8) -> list[str]:
    return [str(value) for value in values[:limit]]


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _frontmatter_list(values: list[str]) -> str:
    return "[" + ", ".join(_quote(value) for value in values) + "]"


def _frontmatter(
    *,
    page_id: str,
    title: str,
    kind: str,
    source_path: str,
    source_type: str,
    status: str,
    summary: str,
    nav_section: str,
    nav_position: int,
    canonical_sources: list[dict[str, str]],
    references: list[str],
    output_path: str,
) -> str:
    lines = [
        "---",
        'schema_version: "0.1"',
        f"page_id: {_quote(page_id)}",
        f"title: {_quote(title)}",
        f"kind: {_quote(kind)}",
        'audience: ["operator", "agent", "maintainer"]',
        f"source_type: {_quote(source_type)}",
        f"source_path: {_quote(source_path)}",
        "source_of_truth: true",
        f"status: {_quote(status)}",
        f"summary: {_quote(summary)}",
        "nav:",
        f"  section: {_quote(nav_section)}",
        f"  position: {nav_position}",
        "canonical_sources:",
    ]
    for source in canonical_sources:
        lines.append(f"  - path: {_quote(source['path'])}")
        lines.append(f"    role: {_quote(source['role'])}")
        if source.get("anchor"):
            lines.append(f"    anchor: {_quote(source['anchor'])}")
    lines.append(f"references: {_frontmatter_list(references)}")
    lines.extend(
        [
            "html:",
            "  render: true",
            f"  output_path: {_quote(output_path)}",
            (
                '  preview_index_path: '
                '"docs/_views/workflow_handbook_reference_index.json"'
            ),
            "---",
            "",
        ]
    )
    return "\n".join(lines)


def _skill_contract_source(skill: str) -> list[dict[str, str]]:
    return [
        {
            "path": "schemas/skill_contracts.json",
            "role": "skill_contract",
            "anchor": skill,
        },
        {
            "path": f".agents/skills/{skill}/SKILL.md",
            "role": "skill_source",
        },
    ]


def render_stage_cards(root: Path) -> str:
    contracts = {
        str(contract.get("skill")): contract for contract in load_contracts(root)
    }
    specs_by_stage = {stage_id: spec for stage_id, *spec in STAGE_SPECS}
    lines: list[str] = [
        "# Harness Workflow Stage Cards",
        "",
        "本文件由 `schemas/skill_contracts.json` 生成，是 operator 的 Stage 速查入口。",
        "它只回答每个 Stage 怎么启动、完成后得到什么、去哪里读深层细节。",
        (
            "完整推荐读取、声明路径、artifact 输出和 Gate 条件保留在 "
            "Stage / Skill 详情页。"
        ),
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
        "Stage -> 一句话 -> 怎么启动 -> 完成后得到 -> 深入阅读",
        "```",
        "",
    ]
    for group_title, group_summary, stage_ids in STAGE_GROUPS:
        lines.extend(
            [
                f"## {group_title}",
                "",
                group_summary,
                "",
            ]
        )
        for stage_id in stage_ids:
            spec = specs_by_stage.get(stage_id)
            if spec is None:
                raise ValueError(f"missing Stage spec for {stage_id}")
            _page_id, title, skill = spec
            contract = contracts.get(skill)
            if contract is None:
                raise ValueError(f"missing Skill Contract for {skill}")
            guidance = STAGE_GUIDANCE[stage_id]
            lines.extend(
                [
                    f"### {title}",
                    "",
                    f"一句话: {guidance['intent']}",
                    "",
                    f"怎么启动: {guidance['start']}",
                    "",
                    f"完成后得到: {guidance['effect']}",
                    "",
                    (
                        "深入阅读: "
                        f"[[stage:{stage_id}|{stage_id} details]], "
                        f"[[skill:{skill}|{skill} Skill]]"
                    ),
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def render_skill_page(root: Path, contract: dict[str, Any], position: int) -> str:
    skill = str(contract.get("skill", "<unknown>"))
    skill_file = root / ".agents" / "skills" / skill / "SKILL.md"
    description = _frontmatter_description(skill_file) or "See the skill file."
    source_path = f"workflow_handbook/skills/{skill}.md"
    references = [
        f"skill:{skill}",
        f"source:schemas/skill_contracts.json#{skill}",
        "term:Gate Evidence",
    ]
    body = [
        _frontmatter(
            page_id=skill,
            title=skill,
            kind="skill",
            source_path=source_path,
            source_type="generated",
            status="generated",
            summary=description,
            nav_section="skills",
            nav_position=position,
            canonical_sources=_skill_contract_source(skill),
            references=references,
            output_path=f"docs/_site/workflow_handbook/skills/{skill}.html",
        ),
        f"# {skill}",
        "",
        "## Purpose",
        "",
        description,
        "",
        "## Triggers",
        "",
        _list_items(_first_values(contract.get("triggers", []), limit=32)),
        "",
        "## Can Write",
        "",
        _list_items(_write_paths(contract)),
        "",
        "## Final Outputs",
        "",
        _list_items(_artifact_outputs(contract, final=True)),
        "",
        "## Tool-Owned Outputs",
        "",
        _list_items(_artifact_outputs(contract, requires_tool=True)),
        "",
        "## Must Read",
        "",
        _list_items(_read_paths(contract)),
        "",
        "## Must Prove",
        "",
        _list_items(
            _first_values(contract.get("required_actions", []), limit=32)
            + _first_values(contract.get("gate_ledger_required_when", []), limit=32)
        ),
        "",
        "## Cannot Do",
        "",
        _list_items(_first_values(contract.get("forbidden_actions", []), limit=32)),
        "",
        "## Exit Condition",
        "",
        (
            "Recommended reads have been considered; durable writes stay "
            "aligned with declared path ownership; Gate ledger reports "
            "command, result, reason, and artifacts when gate conditions are "
            "touched."
        ),
        "",
        "## Related References",
        "",
        _reference_items(references),
    ]
    return "\n".join(body).rstrip() + "\n"


def render_stage_page(
    root: Path,
    contract: dict[str, Any],
    *,
    stage_id: str,
    page_id: str,
    title: str,
    position: int,
) -> str:
    skill = str(contract.get("skill", "<unknown>"))
    skill_file = root / ".agents" / "skills" / skill / "SKILL.md"
    guidance = STAGE_GUIDANCE[stage_id]
    description = guidance["intent"]
    detailed_description = _frontmatter_description(skill_file) or f"{title} stage."
    source_path = f"workflow_handbook/stages/{page_id}.md"
    references = [
        f"stage:{stage_id}",
        f"skill:{skill}",
        f"source:schemas/skill_contracts.json#{skill}",
        "term:Gate Evidence",
    ]
    body = [
        _frontmatter(
            page_id=page_id,
            title=title,
            kind="stage",
            source_path=source_path,
            source_type="generated",
            status="generated",
            summary=description,
            nav_section="stages",
            nav_position=position,
            canonical_sources=_skill_contract_source(skill),
            references=references,
            output_path=f"docs/_site/workflow_handbook/stages/{page_id}.html",
        ),
        f"# {title}",
        "",
        "## Purpose",
        "",
        description,
        "",
        "## How To Run",
        "",
        guidance["start"],
        "",
        "## Completion Effect",
        "",
        guidance["effect"],
        "",
        "## Contract Detail",
        "",
        detailed_description,
        "",
        "## Inputs",
        "",
        _list_items(_first_values(contract.get("triggers", []), limit=32)),
        "",
        "## Outputs",
        "",
        _list_items(_artifact_outputs(contract)),
        "",
        "## Required Reads",
        "",
        _list_items(_read_paths(contract)),
        "",
        "## Gates",
        "",
        _list_items(
            _first_values(contract.get("required_actions", []), limit=32)
            + _first_values(contract.get("gate_ledger_required_when", []), limit=32)
        ),
        "",
        "## Exit Condition",
        "",
        (
            "The stage has produced its declared outputs or explicit `NOT_RUN` "
            "results, and the operator has any required decision or approval context."
        ),
        "",
        "## Related Skills",
        "",
        f"- [[skill:{skill}]]",
        "",
        "## Related References",
        "",
        _reference_items(references),
    ]
    return "\n".join(body).rstrip() + "\n"


def render_skill_pages(root: Path) -> dict[str, str]:
    contracts = load_contracts(root)
    return {
        f"skills/{contract['skill']}.md": render_skill_page(root, contract, index * 10)
        for index, contract in enumerate(contracts)
    }


def render_stage_pages(root: Path) -> dict[str, str]:
    contracts = {
        str(contract.get("skill")): contract for contract in load_contracts(root)
    }
    pages: dict[str, str] = {}
    for index, (stage_id, page_id, title, skill) in enumerate(STAGE_SPECS):
        contract = contracts.get(skill)
        if contract is None:
            raise ValueError(f"missing Skill Contract for {skill}")
        pages[f"stages/{page_id}.md"] = render_stage_page(
            root,
            contract,
            stage_id=stage_id,
            page_id=page_id,
            title=title,
            position=index * 10,
        )
    return pages


def write_generated_pages(
    root: Path,
    pages_output: Path,
    *,
    generate_skill_pages: bool,
    generate_stage_pages: bool,
) -> list[Path]:
    output_root = pages_output if pages_output.is_absolute() else root / pages_output
    pages: dict[str, str] = {}
    if generate_skill_pages:
        pages.update(render_skill_pages(root))
    if generate_stage_pages:
        pages.update(render_stage_pages(root))
    written: list[Path] = []
    for relative, rendered in sorted(pages.items()):
        path = output_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        written.append(path)
    return written


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
    parser.add_argument(
        "--pages-output",
        type=Path,
        default=Path("workflow_handbook"),
        help="Root directory for generated workflow handbook split pages.",
    )
    parser.add_argument("--generate-skill-pages", action="store_true")
    parser.add_argument("--generate-stage-pages", action="store_true")
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
    if args.generate_skill_pages or args.generate_stage_pages:
        write_generated_pages(
            root,
            args.pages_output,
            generate_skill_pages=args.generate_skill_pages,
            generate_stage_pages=args.generate_stage_pages,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
