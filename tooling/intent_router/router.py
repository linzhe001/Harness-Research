#!/usr/bin/env python3
"""Small deterministic router for Harness research workflow prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

ROUTES = {
    "grill",
    "prepare",
    "build",
    "run",
    "analyze",
    "write",
    "change",
    "code-review",
    "code-debug",
    "harness-maintenance",
    "unknown",
}

INTENT_CLASSES = {
    "research_ideation",
    "execution_prepare",
    "initial_build",
    "experiment_run",
    "result_analysis",
    "paper_write",
    "post_build_change",
    "code_review",
    "code_write",
    "harness_maintenance",
    "question",
    "unknown",
}


@dataclass(frozen=True)
class Rule:
    route: str
    intent_class: str
    confidence: str
    next_safe_action: str
    patterns: tuple[str, ...]


RULES: tuple[Rule, ...] = (
    Rule(
        route="harness-maintenance",
        intent_class="harness_maintenance",
        confidence="high",
        next_safe_action=(
            "Use harness-maintenance; read hook, schema, skill, and supervisor "
            "contracts before durable edits."
        ),
        patterns=(
            r"\bharness[_ -]?research\b",
            r"\bworkflow[_ -]?supervisor\b",
            r"\bcodex[_ -]?hooks?\b",
            r"\bhooks?\b.*(?:intent|route|routing|trigger)",
            r"\bskill(?:s)?\b.*(?:sync|contract|shared|adapter)",
            r"\bAGENTS\.md\b|\bCLAUDE\.md\b",
            r"\.agents/|\.claude/",
            r"\bOthers/claude-scholar\b",
            r"意图识别|触发|hook|共享.*skill|skill.*共享",
        ),
    ),
    Rule(
        route="grill",
        intent_class="research_ideation",
        confidence="high",
        next_safe_action=(
            "Use grill; clarify idea, evidence search, claim boundary, and "
            "approved readiness candidates."
        ),
        patterns=(
            r"\bgrill\b",
            r"\bidea\b.*(?:iterate|debate|clarify|research)",
            r"\bliterature\b|\bsurvey\b|\bpaper search\b",
            r"文献|调研|构思|想法|idea|对话迭代|研究目标",
        ),
    ),
    Rule(
        route="prepare",
        intent_class="execution_prepare",
        confidence="high",
        next_safe_action=(
            "Use prepare; consume approved Grill readiness, acquire datasets, "
            "clone baselines, and run baseline smoke checks."
        ),
        patterns=(
            r"\bprepare\b",
            r"\bdataset\b.*(?:download|acquire|prepare|clone)",
            r"\bbaseline\b.*(?:clone|run|reproduce|smoke)",
            r"下载.*数据集|数据集.*下载|克隆.*baseline|跑通.*baseline|准备数据",
        ),
    ),
    Rule(
        route="build",
        intent_class="initial_build",
        confidence="high",
        next_safe_action=(
            "Use build; plan and implement the initial codebase from Grill "
            "intent plus prepared data and baselines."
        ),
        patterns=(
            r"\bbuild\b",
            r"\binitial\b.*(?:codebase|implementation)",
            r"\bcodebase\b.*(?:plan|implementation|scaffold)",
            r"搭建.*代码库|基础.*代码库|主要代码库|implementation.*代码",
        ),
    ),
    Rule(
        route="run",
        intent_class="experiment_run",
        confidence="high",
        next_safe_action=(
            "Use run/iterate; make bounded experiment deltas, execute, and "
            "record metrics and artifacts."
        ),
        patterns=(
            r"\brun\b.*(?:experiment|ablation|sweep|analysis|visualization)",
            r"\bexperiment\b|\bablation\b|\bhyperparameter\b|\bsweep\b",
            r"\bvisuali[sz]ation\b|\bquantitative\b",
            r"实验|消融|超参数|可视化|定量分析|模型架构探索",
        ),
    ),
    Rule(
        route="analyze",
        intent_class="result_analysis",
        confidence="high",
        next_safe_action=(
            "Use analyze/evaluate; turn run outputs into claims, failure modes, "
            "and the next run or write decision."
        ),
        patterns=(
            r"\banaly[sz]e\b|\banalysis\b",
            r"\bresults?\b.*(?:interpret|explain|insight)",
            r"分析.*结果|结果.*分析|见解|指导下一轮",
        ),
    ),
    Rule(
        route="write",
        intent_class="paper_write",
        confidence="high",
        next_safe_action=(
            "Use write; edit paper, repo documentation, release notes, or "
            "GitHub Pages from explicit evidence."
        ),
        patterns=(
            r"\bwrite\b.*(?:paper|manuscript|readme|docs|github pages)",
            r"\bpaper\b|\bmanuscript\b|\bsubmission\b|\bgithub pages\b",
            r"论文|写作|文章|github pages|README|文档完善",
        ),
    ),
    Rule(
        route="change",
        intent_class="post_build_change",
        confidence="medium",
        next_safe_action=(
            "Use change-intake; classify the mature-codebase delta before "
            "routing to run, build, or a small code change."
        ),
        patterns=(
            r"\bchange\b|\bdelta\b",
            r"\bnew research direction\b",
            r"修改.*已有|新的方向|改一下当前|后续修改",
        ),
    ),
    Rule(
        route="code-review",
        intent_class="code_review",
        confidence="high",
        next_safe_action=(
            "Use code-review; inspect bugs, regressions, and test gaps before "
            "any subject-file edits."
        ),
        patterns=(
            r"\breview\b.*(?:code|diff|pr)",
            r"\bcode review\b|\bPR review\b",
            r"代码审查|review.*代码|审一下",
        ),
    ),
    Rule(
        route="code-debug",
        intent_class="code_write",
        confidence="medium",
        next_safe_action=(
            "Use code-debug; make a narrow implementation or fix under the "
            "project code surface."
        ),
        patterns=(
            r"\bfix\b|\bbug\b|\bdebug\b|\bimplement\b",
            r"修复|实现|改代码|报错",
        ),
    ),
)


def route_prompt(prompt: str) -> dict[str, Any]:
    text = prompt.strip()
    lowered = _normalize(text)
    matches: list[tuple[int, Rule, list[str]]] = []
    for order, rule in enumerate(RULES):
        reason_codes = [
            f"{rule.route}:{index}"
            for index, pattern in enumerate(rule.patterns)
            if re.search(pattern, lowered, flags=re.IGNORECASE)
        ]
        if reason_codes:
            score = _confidence_score(rule.confidence) * 100 - order
            score += min(len(reason_codes), 3) * 5
            matches.append((score, rule, reason_codes))

    if matches:
        _score, rule, reason_codes = sorted(matches, key=lambda item: item[0])[-1]
        return _payload(
            prompt=text,
            route=rule.route,
            intent_class=rule.intent_class,
            confidence=rule.confidence,
            reason_codes=reason_codes,
            next_safe_action=rule.next_safe_action,
        )

    intent_class = "question" if _looks_question(lowered) else "unknown"
    return _payload(
        prompt=text,
        route="unknown",
        intent_class=intent_class,
        confidence="low",
        reason_codes=["no_rule_match"],
        next_safe_action=(
            "Do not auto-route; ask for clarification or use local context."
        ),
    )


def validate_route_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be 1")
    route = payload.get("route")
    if route not in ROUTES:
        errors.append(f"route must be one of {sorted(ROUTES)}")
    intent_class = payload.get("intent_class")
    if intent_class not in INTENT_CLASSES:
        errors.append(f"intent_class must be one of {sorted(INTENT_CLASSES)}")
    confidence = payload.get("confidence")
    if confidence not in {"high", "medium", "low"}:
        errors.append("confidence must be high, medium, or low")
    for key in ("prompt_hash", "prompt_preview", "next_safe_action"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} must be a non-empty string")
    if not isinstance(payload.get("reason_codes"), list):
        errors.append("reason_codes must be a list")
    return errors


def _payload(
    *,
    prompt: str,
    route: str,
    intent_class: str,
    confidence: str,
    reason_codes: list[str],
    next_safe_action: str,
) -> dict[str, Any]:
    preview = prompt.replace("\n", " ").strip()
    if len(preview) > 280:
        preview = preview[:277].rstrip() + "..."
    return {
        "schema_version": SCHEMA_VERSION,
        "route": route,
        "intent_class": intent_class,
        "confidence": confidence,
        "source": "heuristic_router",
        "reason_codes": reason_codes,
        "next_safe_action": next_safe_action,
        "prompt_hash": "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_preview": preview or "<empty>",
    }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _looks_question(text: str) -> bool:
    return bool(
        "?" in text
        or "？" in text
        or re.search(r"\b(?:how|what|why|should|can|could)\b", text)
        or re.search(r"怎么|如何|是否|能否|吗", text)
    )


def _confidence_score(confidence: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(confidence, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route a Harness prompt.")
    parser.add_argument("prompt", nargs="?", default="")
    parser.add_argument("--prompt-file")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    payload = route_prompt(prompt)
    errors = validate_route_payload(payload)
    if errors:
        print("; ".join(errors), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['route']} {payload['confidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
