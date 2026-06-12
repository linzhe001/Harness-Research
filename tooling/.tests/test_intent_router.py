from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "intent_router"))

import route_examples  # noqa: E402
import router  # noqa: E402


def test_router_classifies_research_workflow_stages() -> None:
    cases = {
        "grill 应该一边询问用户一边进行文献检索": "grill",
        "prepare 下载数据集并克隆 baseline": "prepare",
        "build 负责基础代码库 plan 和 implementation": "build",
        "run 做超参数调节、消融实验和可视化": "run",
        "analyze 根据结果产生有意义的分析": "analyze",
        "write 论文并完善 README 和 GitHub Pages": "write",
    }

    for prompt, expected in cases.items():
        route = router.route_prompt(prompt)
        assert route["route"] == expected
        assert not router.validate_route_payload(route)


def test_router_prefers_harness_maintenance_for_hook_skill_work() -> None:
    route = router.route_prompt(
        "hook 的意图判断怎么完善，并把 Codex 和 Claude skill 共享起来"
    )

    assert route["route"] == "harness-maintenance"
    assert route["intent_class"] == "harness_maintenance"
    assert route["confidence"] == "high"


def test_approved_route_examples_validate() -> None:
    assert route_examples.command_validate(
        route_examples.build_parser().parse_args(["validate"])
    ) == 0


def test_route_example_add_collects_pending_misclassification(tmp_path: Path) -> None:
    output = tmp_path / "pending.jsonl"

    code = route_examples.main(
        [
            "add",
            "--prompt",
            "这个 hook route 应该是 prepare 但误判了",
            "--expected-route",
            "prepare",
            "--expected-intent",
            "execution_prepare",
            "--observed-route",
            "harness-maintenance",
            "--reason",
            "operator marked a hook-routing correction",
            "--output",
            str(output),
        ]
    )

    assert code == 0
    rows = [
        json.loads(line)
        for line in output.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[0]["expected_route"] == "prepare"
    assert rows[0]["observed_route"] == "harness-maintenance"

