from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

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
        "prepare_acquisition_plan",
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


def test_node_registry_rejects_invalid_automation_policy() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)
    invalid = copy.deepcopy(registry)
    invalid["nodes"][0]["automation_policy"] = {
        "profile": "automation_prepare",
        "goal_max_chars": 0,
        "unknown_budget": 1,
    }

    errors = workflow_ctl.validate_node_registry(REPO_ROOT, invalid)

    assert any(
        "automation_policy.goal_max_chars must be a positive integer" in e
        for e in errors
    )
    assert any("unknown automation_policy field unknown_budget" in e for e in errors)


def test_prepare_acquisition_nodes_require_machine_manifests() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)
    nodes = {node["node_id"]: node for node in registry["nodes"]}

    plan_conditions = nodes["prepare_acquisition_plan"]["postconditions"]
    data_conditions = nodes["prepare_data_prep"]["postconditions"]
    baseline_conditions = nodes["prepare_baseline_repro"]["postconditions"]

    assert {
        "type": "artifact_matches_schema",
        "path": ".workflow_supervisor/runs/<run_id>/runtime/acquisition_plan.json",
        "schema": "schemas/acquisition_plan.schema.json",
    } in plan_conditions
    assert {
        "type": "artifact_matches_schema",
        "path": "data/dataset_manifest.json",
        "schema": "schemas/dataset_acquisition_manifest.schema.json",
    } in data_conditions
    assert {
        "type": "artifact_matches_schema",
        "path": "baselines/baseline_manifest.json",
        "schema": "schemas/baseline_acquisition_manifest.schema.json",
    } in baseline_conditions
    assert "data/" in nodes["prepare_data_prep"]["allowed_worker_write_patterns"]
    assert "acquisition evidence" in nodes["prepare_baseline_repro"]["purpose"]


def test_supervisor_nodes_do_not_own_docs_site_outputs() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)

    for node in registry["nodes"]:
        owned_outputs = node.get("tool_owned_output_refs", [])
        assert "docs/_views/" not in owned_outputs
        assert "docs/_site/" not in owned_outputs


def test_build_code_debug_is_failure_recovery_node() -> None:
    registry = workflow_ctl.load_node_registry(REPO_ROOT)
    nodes = {node["node_id"]: node for node in registry["nodes"]}
    normal_build_nodes = [
        node["node_id"]
        for node in workflow_ctl.ordered_segment_nodes(registry, "build")
    ]

    assert nodes["build_code_debug"]["run_when"] == "on_failure"
    assert "build_code_debug" not in normal_build_nodes
    assert [
        node["node_id"]
        for node in workflow_ctl.on_failure_nodes(registry, "build")
    ] == ["build_code_debug"]


def test_gate_policy_risk_matrix_has_prepare_automation_profile() -> None:
    policy_path = (
        REPO_ROOT / "tooling" / "workflow_supervisor" / "config" / "gate_policy.yaml"
    )
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    profiles = policy["profiles"]

    assert profiles["default"]["missing_recommended_reads"] == "warn_once"
    assert profiles["default"]["tool_owned_runtime_writes"] == "block"
    assert profiles["default"]["external_downloads"] == "require_run_policy"
    prepare = profiles["automation_prepare"]
    assert prepare["inherits"] == "default"
    assert prepare["external_downloads"] == "allow_if_readiness_approved"
    assert "data/**" in prepare["allow_write_globs"]
    assert "baselines/**" in prepare["allow_write_globs"]
    assert (
        ".workflow_supervisor/runs/<run_id>/runtime/acquisition_plan.json"
        in prepare["require_postconditions"]
    )
    assert "data/dataset_manifest.json" in prepare["require_postconditions"]
    assert "baselines/baseline_manifest.json" in prepare["require_postconditions"]
