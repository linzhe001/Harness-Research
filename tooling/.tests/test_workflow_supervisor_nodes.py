from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tooling" / "workflow_supervisor" / "scripts"))

import workflow_ctl  # noqa: E402


def test_default_node_registry_validates() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)

    errors = workflow_ctl.validate_node_registry(REPO_ROOT, registry)

    assert errors == []


def test_slice5_nodes_are_registered() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)
    node_ids = {node["node_id"] for node in registry["nodes"]}

    assert {
        "prepare_data_prep",
        "prepare_baseline_repro",
        "build_refine_arch",
        "build_plan",
        "build_code_expert",
        "build_code_debug",
        "build_validate_run",
        "release_final_exp_matrix",
        "release_claim_approval",
    }.issubset(node_ids)


def test_evidence_outputs_are_tool_owned_not_worker_writes() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)

    for node in registry["nodes"]:
        allowed = node["allowed_worker_write_patterns"]
        tool_owned = node["tool_owned_output_refs"]
        assert not any(path.startswith(".evidence/") for path in allowed)
        for tool in node["evidence_tools"]:
            for output in tool["outputs"]:
                if output.startswith(".evidence/"):
                    assert output in tool_owned


def test_node_registry_rejects_auto_node_without_postconditions() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)
    invalid = copy.deepcopy(registry)
    invalid["nodes"][0]["postconditions"] = []

    errors = workflow_ctl.validate_node_registry(REPO_ROOT, invalid)

    assert any("auto_allowed nodes require postconditions" in e for e in errors)


def test_node_registry_rejects_worker_write_to_supervisor_runtime() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)
    invalid = copy.deepcopy(registry)
    invalid["nodes"][0]["allowed_worker_write_patterns"].append(
        ".workflow_supervisor/"
    )

    errors = workflow_ctl.validate_node_registry(REPO_ROOT, invalid)

    assert any("tool-owned path .workflow_supervisor/" in e for e in errors)
